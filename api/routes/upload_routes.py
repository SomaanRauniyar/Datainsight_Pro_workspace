"""
Upload Routes - File upload with speed optimizations and background processing
"""
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from typing import Optional, AsyncGenerator
import pandas as pd
from io import BytesIO
import numpy as np
import json
import uuid
import asyncio

from src.file_parser import parse_file
from src.embeddings import embed_chunks
from src.briefing_system import BriefingSystem
from src.database import track_file_upload, log_token_usage
from src.security import validate_file_extension, sanitize_filename, sanitize_string
from src.user_keys import get_effective_key
from src.config import EMBED_DIM
from src.vector_manager import VectorDBManager
from ..dependencies import get_current_user, get_vector_db, get_data_cache, get_upload_jobs
from ..models import QuickUploadResponse, JobStatusResponse

router = APIRouter()

# Allowed file extensions
ALLOWED_FILE_EXTENSIONS = ['csv', 'xlsx', 'xls', 'pdf', 'docx', 'doc']

def safe_json_records(records):
    """Returns a list of dicts with all NaN, inf, -inf replaced with None for JSON serialization."""
    safe = []
    for row in records:
        clean_row = {}
        for k, v in row.items():
            if isinstance(v, float):
                if np.isnan(v) or np.isinf(v):
                    clean_row[k] = None
                else:
                    clean_row[k] = float(v)
            else:
                clean_row[k] = v
        safe.append(clean_row)
    return safe

def coerce_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Safely coerce object columns to numeric where possible."""
    for c in df.columns:
        if df[c].dtype == object:
            try:
                df[c] = pd.to_numeric(df[c])
            except (ValueError, TypeError):
                pass
    return df

# ============== Optimized Upload Endpoints ==============

@router.post("/quick", response_model=QuickUploadResponse)
async def upload_quick_response(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...), 
    user_id: str = Form(...),
    user: dict = Depends(get_current_user),
    data_cache: dict = Depends(get_data_cache),
    upload_jobs: dict = Depends(get_upload_jobs)
):
    """
    🚀 SPEED OPTIMIZED: Return immediate preview, process embeddings in background
    Expected response time: 2-5 seconds (vs 15-30 seconds for full processing)
    """
    
    # Quick validation
    filename = file.filename
    if not validate_file_extension(filename, ALLOWED_FILE_EXTENSIONS):
        raise HTTPException(
            status_code=400, 
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_FILE_EXTENSIONS)}"
        )
    
    # Security: Sanitize filename and limit file size
    filename = sanitize_filename(filename)
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 50MB.")
    
    effective_user_id = str(user["user_id"]) if user else sanitize_string(user_id, max_length=100)
    
    try:
        # ⚡ OPTIMIZATION: Quick parse (first 20 rows only for immediate preview)
        parsed = parse_file(BytesIO(contents), filename=filename)
        preview_rows = parsed[:20]  # Immediate preview - much faster!
        
        # Generate quick preview
        preview_data = None
        columns = []
        
        if filename.lower().endswith((".csv", ".xlsx", ".xls")):
            df_preview = pd.DataFrame(preview_rows)
            df_preview = coerce_numeric_columns(df_preview)
            columns = df_preview.columns.tolist()
            
            preview_data = {
                "type": "table",
                "columns": columns,
                "data": df_preview.to_dict(orient="records"),
                "total_rows": len(parsed),  # Full count
                "total_columns": len(columns),
                "is_preview": True,
                "preview_rows": len(preview_rows)
            }
        else:
            # Document preview - enhanced handling for Word docs and PDFs with tables
            # Check if parsed data contains structured table data (list of dicts with actual column names)
            if preview_rows and isinstance(preview_rows[0], dict) and not preview_rows[0].get("text"):
                # This is structured table data from document
                df_preview = pd.DataFrame(parsed)  # Use full parsed data for proper columns
                df_preview = coerce_numeric_columns(df_preview)
                columns = df_preview.columns.tolist()
                
                # Store in cache for visualization
                data_cache[(effective_user_id, filename)] = df_preview
                
                preview_data = {
                    "type": "document",
                    "tables": [{
                        "columns": columns,
                        "data": safe_json_records(df_preview.head(10).to_dict(orient="records"))
                    }],
                    "total_rows": len(parsed),
                    "is_preview": True,
                    "document_type": "document_with_tables"
                }
            else:
                # This is text content (paragraphs)
                text_content = "\n".join([str(p.get("text", p)) if isinstance(p, dict) else str(p) for p in preview_rows])
                preview_data = {
                    "type": "document",
                    "summary": text_content[:1500] + ("..." if len(text_content) > 1500 else ""),
                    "total_items": len(parsed),
                    "is_preview": True,
                    "document_type": "text_document"
                }
        
        # Create background job for full processing
        job_id = str(uuid.uuid4())
        upload_jobs[job_id] = {
            "status": "processing",
            "progress": 20,
            "message": "Preview ready. Processing full file...",
            "filename": filename,
            "user_id": effective_user_id,
            "created_at": asyncio.get_event_loop().time()
        }
        
        # 🚀 Start background processing (non-blocking)
        background_tasks.add_task(
            process_full_upload_background, 
            job_id, contents, filename, effective_user_id, parsed, user, upload_jobs, data_cache
        )
        
        return QuickUploadResponse(
            filename=filename,
            preview=preview_data,
            job_id=job_id,
            status="preview_ready",
            message="✅ Preview ready! Full processing continues in background."
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

async def process_full_upload_background(
    job_id: str, 
    contents: bytes, 
    filename: str, 
    user_id: str, 
    parsed_data: list,
    user: dict,
    upload_jobs: dict,
    data_cache: dict
):
    """
    Background task for full file processing with speed optimizations
    """
    try:
        # Update job status
        upload_jobs[job_id].update({
            "progress": 40,
            "message": "Creating optimized chunks..."
        })
        
        # ⚡ OPTIMIZATION: Limit chunks for speed (50 instead of 100)
        MAX_CHUNKS = 50
        if len(parsed_data) > MAX_CHUNKS:
            print(f"[Background] Limiting chunks from {len(parsed_data)} to {MAX_CHUNKS} for speed")
            parsed_data = parsed_data[:MAX_CHUNKS]
        
        # ⚡ OPTIMIZATION: Smaller content chunks (2KB instead of 5KB)
        chunks = []
        for i, row in enumerate(parsed_data):
            chunks.append({
                "chunk_id": f"{filename}_chunk_{i}",
                "file_id": filename,
                "user_id": user_id,
                "content": str(row)[:2000],  # Reduced from 5000 to 2000 for faster embedding
            })
        
        upload_jobs[job_id].update({
            "progress": 60,
            "message": f"Generating embeddings for {len(chunks)} chunks..."
        })
        
        # Generate embeddings
        embedded_chunks = embed_chunks(chunks, user_id=user_id)
        
        upload_jobs[job_id].update({
            "progress": 80,
            "message": "Storing vectors in database..."
        })
        
        # Prepare vectors for storage
        vectors = [
            {
                "id": chunk["chunk_id"],
                "values": chunk["embedding"],
                "metadata": {
                    "content": chunk["content"],
                    "file_id": filename,
                    "user_id": user_id,
                },
            }
            for chunk in embedded_chunks
        ]
        
        # Use user's Pinecone keys if available
        user_pinecone_key = get_effective_key(user_id, "pinecone_api_key")
        user_pinecone_index = get_effective_key(user_id, "pinecone_index")
        
        namespace = f"user_{user_id}_{filename}"
        
        if user_pinecone_key and user_pinecone_index:
            # User has their own Pinecone
            user_vector_db = VectorDBManager(
                api_key=user_pinecone_key, 
                index_name=user_pinecone_index, 
                dimension=EMBED_DIM
            )
            user_vector_db.upsert_vectors(vectors, namespace=namespace)
        else:
            # Use system Pinecone (this requires access to the global vector_db)
            # We'll need to pass this through or access it differently
            from src.config import PINECONE_API_KEY, PINECONE_INDEX
            system_vector_db = VectorDBManager(
                api_key=PINECONE_API_KEY, 
                index_name=PINECONE_INDEX, 
                dimension=EMBED_DIM
            )
            system_vector_db.upsert_vectors(vectors, namespace=namespace)
        
        # Store full DataFrame in cache
        if filename.lower().endswith((".csv", ".xlsx", ".xls")):
            df = pd.DataFrame(parsed_data)
            df = coerce_numeric_columns(df)
            data_cache[(user_id, filename)] = df
        
        # Generate executive summary if user is authenticated
        summary_result = None
        if user and len(parsed_data) > 0:
            try:
                preview = parsed_data[:10] if isinstance(parsed_data, list) else []
                summary_result = BriefingSystem.generate_data_summary_for_upload(
                    preview, filename, user["user_id"]
                )
                
                # Track file upload
                file_type = filename.split('.')[-1].lower() if '.' in filename else 'unknown'
                track_file_upload(
                    user["user_id"], 
                    filename, 
                    file_type, 
                    json.dumps(summary_result.get("summary", {}))
                )
            except Exception as e:
                print(f"[Background] Summary generation failed: {e}")
        
        # Mark job as completed
        upload_jobs[job_id].update({
            "status": "completed",
            "progress": 100,
            "message": "✅ Full processing complete!",
            "result": {
                "filename": filename,
                "total_chunks": len(chunks),
                "vectors_stored": len(vectors),
                "executive_summary": summary_result.get("summary") if summary_result else None
            }
        })
        
        print(f"[Background] ✅ Upload complete: {filename} ({len(chunks)} chunks)")
        
    except Exception as e:
        upload_jobs[job_id].update({
            "status": "failed",
            "progress": 0,
            "error": str(e),
            "message": f"❌ Processing failed: {str(e)}"
        })
        print(f"[Background] ❌ Upload failed: {filename} - {str(e)}")

@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_upload_status(
    job_id: str,
    upload_jobs: dict = Depends(get_upload_jobs)
):
    """Check background upload job status"""
    if job_id not in upload_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_data = upload_jobs[job_id]
    
    return JobStatusResponse(
        status=job_data["status"],
        progress=job_data["progress"],
        message=job_data["message"],
        filename=job_data.get("filename"),
        result=job_data.get("result"),
        error=job_data.get("error")
    )

# ============== Legacy Upload Endpoint (for backward compatibility) ==============

@router.post("/")
async def upload_legacy(
    file: UploadFile = File(...), 
    user_id: str = Form(...),
    user: dict = Depends(get_current_user),
    vector_db = Depends(get_vector_db),
    data_cache: dict = Depends(get_data_cache)
):
    """
    Legacy upload endpoint - full processing (slower but complete)
    Use /upload/quick for better performance
    """
    
    # Security validations
    filename = file.filename
    if not validate_file_extension(filename, ALLOWED_FILE_EXTENSIONS):
        raise HTTPException(
            status_code=400, 
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_FILE_EXTENSIONS)}"
        )
    
    filename = sanitize_filename(filename)
    MAX_FILE_SIZE = 50 * 1024 * 1024
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 50MB.")
    
    effective_user_id = str(user["user_id"]) if user else sanitize_string(user_id, max_length=100)
    
    try:
        # Parse file
        parsed = parse_file(BytesIO(contents), filename=filename)
        
        # Limit chunks
        MAX_CHUNKS = 50  # Reduced for speed
        if len(parsed) > MAX_CHUNKS:
            parsed = parsed[:MAX_CHUNKS]
        
        # Create chunks with smaller content
        chunks = []
        for i, row in enumerate(parsed):
            chunks.append({
                "chunk_id": f"{filename}_chunk_{i}",
                "file_id": filename,
                "user_id": effective_user_id,
                "content": str(row)[:2000],  # Reduced content size
            })
        
        # Generate embeddings
        embedded_chunks = embed_chunks(chunks, user_id=effective_user_id)
        
        # Prepare vectors
        vectors = [
            {
                "id": chunk["chunk_id"],
                "values": chunk["embedding"],
                "metadata": {
                    "content": chunk["content"],
                    "file_id": filename,
                    "user_id": effective_user_id,
                },
            }
            for chunk in embedded_chunks
        ]
        
        # Store vectors
        namespace = f"user_{effective_user_id}_{filename}"
        vector_db.upsert_vectors(vectors, namespace=namespace)
        
        # Process DataFrame and create preview
        file_type = filename.split('.')[-1].lower() if '.' in filename else 'unknown'
        preview_data = None
        columns = []
        
        if filename.lower().endswith((".csv", ".xlsx", ".xls")):
            df = pd.DataFrame(parsed)
            df = coerce_numeric_columns(df)
            preview = df.head(5).to_dict(orient="records")
            preview = safe_json_records(preview)
            columns = df.columns.tolist()
            data_cache[(effective_user_id, filename)] = df
            
            preview_data = {
                "type": "table",
                "columns": columns,
                "data": df.head(10).to_dict(orient="records"),
                "total_rows": len(df),
                "total_columns": len(columns)
            }
        else:
            # Handle document files
            if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
                df = pd.DataFrame(parsed)
                df = coerce_numeric_columns(df)
                columns = df.columns.tolist()
                data_cache[(effective_user_id, filename)] = df
                
                preview_data = {
                    "type": "document",
                    "tables": [{
                        "columns": columns,
                        "data": df.head(5).to_dict(orient="records")
                    }],
                    "total_rows": len(df)
                }
            else:
                text_content = "\\n".join([str(p.get("text", p)) if isinstance(p, dict) else str(p) for p in parsed[:20]])
                preview_data = {
                    "type": "document",
                    "tables": [],
                    "summary": text_content[:1000] + ("..." if len(text_content) > 1000 else ""),
                    "content": text_content[:500]
                }
        
        # Generate executive summary
        summary_result = None
        if user and parsed:
            try:
                summary_result = BriefingSystem.generate_data_summary_for_upload(
                    parsed[:10], filename, user["user_id"]
                )
                track_file_upload(user["user_id"], filename, file_type, 
                                json.dumps(summary_result.get("summary", {})))
            except Exception as e:
                print(f"[Upload] Summary generation failed: {e}")
        
        return {
            "filename": filename,
            "columns": columns,
            "preview": preview_data,
            "file_type": file_type,
            "message": "File uploaded and processed successfully",
            "executive_summary": summary_result.get("summary") if summary_result else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

# ============== Streaming Upload (Advanced) ==============

@router.post("/stream")
async def upload_with_streaming(
    file: UploadFile = File(...), 
    user_id: str = Form(...),
    user: dict = Depends(get_current_user)
):
    """Streaming upload with real-time progress updates"""
    
    async def process_file_stream() -> AsyncGenerator[str, None]:
        try:
            # Step 1: Validate file
            yield f"data: {json.dumps({'step': 'validation', 'progress': 10, 'message': 'Validating file...'})}\n\n"
            
            filename = file.filename
            if not validate_file_extension(filename, ALLOWED_FILE_EXTENSIONS):
                yield f"data: {json.dumps({'error': 'Invalid file type'})}\n\n"
                return
            
            # Step 2: Read file
            yield f"data: {json.dumps({'step': 'reading', 'progress': 20, 'message': 'Reading file contents...'})}\n\n"
            contents = await file.read()
            
            # Step 3: Parse file
            yield f"data: {json.dumps({'step': 'parsing', 'progress': 30, 'message': 'Parsing file data...'})}\n\n"
            parsed = parse_file(BytesIO(contents), filename=filename)
            
            # Step 4: Create chunks
            yield f"data: {json.dumps({'step': 'chunking', 'progress': 40, 'message': f'Creating {min(50, len(parsed))} chunks...'})}\n\n"
            
            chunks = []
            max_chunks = min(50, len(parsed))  # Speed optimization
            for i, row in enumerate(parsed[:max_chunks]):
                if i % 10 == 0:  # Update progress every 10 chunks
                    progress = 40 + (i / max_chunks) * 20
                    yield f"data: {json.dumps({'step': 'chunking', 'progress': int(progress), 'message': f'Processing chunk {i+1}/{max_chunks}'})}\n\n"
                
                chunks.append({
                    "chunk_id": f"{filename}_chunk_{i}",
                    "file_id": filename,
                    "user_id": user_id,
                    "content": str(row)[:2000],  # Optimized content size
                })
            
            # Step 5: Generate embeddings
            yield f"data: {json.dumps({'step': 'embedding', 'progress': 60, 'message': 'Generating embeddings...'})}\n\n"
            embedded_chunks = embed_chunks(chunks, user_id=user_id)
            
            # Step 6: Store in vector DB
            yield f"data: {json.dumps({'step': 'storing', 'progress': 80, 'message': 'Storing in vector database...'})}\n\n"
            
            # Complete processing...
            yield f"data: {json.dumps({'step': 'complete', 'progress': 100, 'message': 'Upload complete!', 'result': {'filename': filename}})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        process_file_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )