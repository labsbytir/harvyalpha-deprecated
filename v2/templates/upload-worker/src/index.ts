/**
 * Harvy Upload Worker - Public file upload endpoint
 * Features: Drag-and-drop, R2 streaming, Basin integration
 */

import { R2Bucket } from "cloudflare:workers";

export interface Env {
  HARVY_UPLOAD_BUCKET: R2Bucket;
  HARVY_ARTIFACTS_BUCKET: R2Bucket;
  BASIN_INGEST_URL?: string;
  BASIN_INGEST_TOKEN?: string;
}

interface ProcessedArtifact {
  artifact_id: string;
  artifact_type: 'raw_response' | 'normalized_entity';
  content_type: string;
  content: string;
  encoding: string;
  metadata: {
    file_size: number;
    modified_at: string;
    source_path: string;
    processing_timestamp: string;
    upload_timestamp: string;
  };
  provenance: {
    source_bucket: 'harvy-upload';
    collection_method: 'web_upload';
  };
}

export async function sha256(data: string | ArrayBuffer): Promise<string> {
  const encoder = new TextEncoder();
  const bytes = typeof data === 'string' 
    ? encoder.encode(data) 
    : new Uint8Array(data);
  const hashBuffer = await crypto.subtle.digest('SHA-256', bytes);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

export async function generateArtifactId(sourcePath: string): Promise<string> {
  return `sha256:${await sha256(sourcePath)}`;
}

export async function createArtifact(
  fileName: string,
  content: string,
  contentType: string,
  fileSize: number,
  uploadTimestamp: string,
): ProcessedArtifact {
  const now = new Date().toISOString();
  const sourcePath = `harvy-upload/${fileName}`;
  const artifactId = await generateArtifactId(sourcePath);
  
  return {
    artifact_id: artifactId,
    artifact_type: contentType.startsWith('text/html') || contentType.startsWith('text/plain')
      ? 'raw_response'
      : 'normalized_entity',
    content_type: contentType,
    content,
    encoding: 'utf-8',
    metadata: {
      file_size: fileSize,
      modified_at: now,
      source_path: sourcePath,
      processing_timestamp: now,
      upload_timestamp: uploadTimestamp,
    },
    provenance: {
      source_bucket: 'harvy-upload',
      collection_method: 'web_upload',
    },
  };
}

export async function uploadToBasin(
  artifact: ProcessedArtifact,
  env: Env,
): Promise<boolean> {
  if (!env.BASIN_INGEST_URL) {
    console.warn('BASIN_INGEST_URL not configured');
    return false;
  }
  
  try {
    const payload = JSON.stringify(artifact);
    const response = await fetch(env.BASIN_INGEST_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(env.BASIN_INGEST_TOKEN ? { 'Authorization': `Bearer ${env.BASIN_INGEST_TOKEN}` } : {}),
      },
      body: payload,
    });
    
    if (!response.ok) {
      console.error(`Basin upload failed: ${response.status}`);
      return false;
    }
    
    return true;
  } catch (error) {
    console.error('Basin upload error:', error);
    return false;
  }
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    };
    
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }
    
    // Upload endpoint
    if (request.method === 'POST' && url.pathname === '/api/upload') {
      try {
        const contentType = request.headers.get('Content-Type') || '';
        
        if (contentType.includes('multipart/form-data')) {
          const formData = await request.formData();
          const file = formData.get('file') as File | null;
          
          if (!file) {
            return new Response(JSON.stringify({ error: 'No file provided' }), {
              status: 400,
              headers: { ...corsHeaders, 'Content-Type': 'application/json' },
            });
          }
          
          const fileName = file.name;
          const fileSize = file.size;
          const uploadId = crypto.randomUUID();
          const uploadTimestamp = new Date().toISOString();
          
          // Stream to R2
          await env.HARVY_UPLOAD_BUCKET.put(uploadId, file.stream());
          
          // Read and process content
          const fileBytes = await file.arrayBuffer();
          const fileContent = new TextDecoder().decode(fileBytes);
          
          // Create artifact
          const artifact = await createArtifact(
            fileName,
            fileContent,
            file.type || 'text/plain',
            fileSize,
            uploadTimestamp,
          );
          
          // Save to artifacts bucket
          const artifactKey = `processed/${fileName}.json`;
          await env.HARVY_ARTIFACTS_BUCKET.put(artifactKey, JSON.stringify(artifact));
          
          // Upload to Basin
          await uploadToBasin(artifact, env);
          
          return new Response(JSON.stringify({
            success: true,
            fileId: uploadId,
            fileName,
            fileSize,
            artifactPath: artifactKey,
            artifactId: artifact.artifact_id,
          }), {
            headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          });
        }
        
        return new Response(JSON.stringify({ error: 'Unsupported content type' }), {
          status: 400,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        });
      } catch (error) {
        return new Response(JSON.stringify({ error: 'Upload failed', details: String(error) }), {
          status: 500,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        });
      }
    }
    
    // Health check
    if (request.method === 'GET' && url.pathname === '/health') {
      return new Response(JSON.stringify({
        status: 'ok',
        worker: 'harvy-upload-worker',
        features: ['file-upload', 'r2-storage', 'basin-integration'],
      }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }
    
    // Upload page
    if (request.method === 'GET' && (url.pathname === '/' || url.pathname === '/upload')) {
      const html = `
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Harvy Upload</title>
<style>
:root{--bg:#0a0a0a;--bg-panel:#1a1a1a;--text:#e5e5e5;--text-muted:#a1a1aa;--primary:#3b82f6;--success:#10b981;--danger:#ef4444;--border:#262626;--radius:8px}
body{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--text);line-height:1.6}
.container{max-width:800px;margin:0 auto;padding:2rem}
header{display:flex;justify-content:space-between;align-items:center;margin-bottom:3rem;padding-bottom:1rem;border-bottom:1px solid var(--border)}
.brand{display:flex;align-items:center;gap:12px;text-decoration:none;color:var(--text)}
.brand-logo{width:40px;height:40px;border-radius:50%;background:var(--primary);display:flex;align-items:center;justify-content:center;font-weight:bold;color:white}
h1{font-size:2rem;font-weight:600;margin-bottom:0.5rem}
.subtitle{color:var(--text-muted);font-size:1rem}
.upload-area{border:2px dashed var(--border);border-radius:var(--radius);padding:3rem;text-align:center;transition:all 0.3s;cursor:pointer;background:var(--bg-panel)}
.upload-area:hover{border-color:var(--primary);background:rgba(59,130,246,0.05)}
.upload-area.drag-over{border-color:var(--primary);background:rgba(59,130,246,0.1)}
.upload-icon{font-size:3rem;margin-bottom:1rem;opacity:0.5}
.btn{display:inline-flex;align-items:center;gap:8px;padding:0.75rem 1.5rem;background:var(--primary);color:white;border:none;border-radius:var(--radius);font-weight:500;cursor:pointer;transition:background 0.2s}
.btn:hover{background:#2563eb}
.progress-container{margin-top:2rem;display:none}
.progress-bar{width:100%;height:6px;background:var(--border);border-radius:3px;overflow:hidden;margin-bottom:1rem}
.progress-fill{height:100%;background:var(--primary);width:0%;transition:width 0.3s}
.status{display:flex;align-items:center;gap:8px;margin-bottom:1rem}
.status-icon{width:20px;height:20px;border-radius:50%;background:var(--primary);display:flex;align-items:center;justify-content:center;color:white;font-size:12px}
.file-list{margin-top:2rem}
.file-item{padding:1rem;background:var(--bg-panel);border-radius:var(--radius);margin-bottom:0.5rem}
footer{margin-top:4rem;padding-top:2rem;border-top:1px solid var(--border);color:var(--text-muted);font-size:0.875rem}
@media(max-width:600px){.container{padding:1rem}h1{font-size:1.5rem}}
</style>
</head><body>
<div class="container"><header>
<a href="/" class="brand"><div class="brand-logo">U</div><div><div style="font-weight:600">HARVY UPLOAD</div><div class="subtitle">Public File Ingestion</div></div></a>
</header>
<main>
<h1>Upload Files</h1><p class="subtitle">Drag files here or click to select</p>
<div class="upload-area" id="dropZone">
<div class="upload-icon">📁</div>
<div class="upload-instructions"><strong>Drag & drop files here</strong><br>or</div>
<button class="btn" id="fileInputBtn">📁 Select Files</button>
<input type="file" id="fileInput" multiple style="display:none">
</div>
<div class="progress-container" id="progressContainer" style="display:none">
<div class="status"><div class="status-icon">↻</div><span class="status-text" id="statusText">Ready to upload</span></div>
<div class="progress-bar"><div class="progress-fill" id="progressFill"></div></div>
<div class="file-info" id="fileInfo" style="display:none"><div class="file-name" id="fileName">File name</div><div class="file-size" id="fileSize">0 bytes</div></div>
</div>
<div class="file-list" id="fileList" style="display:none"></div>
</main>
<footer><p>Files streamed to R2 and processed into JSON artifacts.</p></footer>
</div>
<script>
const dropZone=document.getElementById('dropZone'),fileInput=document.getElementById('fileInput'),
fileInputBtn=document.getElementById('fileInputBtn'),progressContainer=document.getElementById('progressContainer'),
fileList=document.getElementById('fileList'),statusText=document.getElementById('statusText'),
progressFill=document.getElementById('progressFill'),fileNameEl=document.getElementById('fileName'),
fileSizeEl=document.getElementById('fileSize');
['dragenter','dragover','dragleave','drop'].forEach(e=>{dropZone.addEventListener(e,p,0);document.body.addEventListener(e,p,0)});
function p(e){e.preventDefault();e.stopPropagation()}
['dragenter','dragover'].forEach(e=>dropZone.addEventListener(e,h,0));
['dragleave','drop'].forEach(e=>dropZone.addEventListener(e,u,0));
function h(){dropZone.classList.add('drag-over')}
function u(){dropZone.classList.remove('drag-over')}
dropZone.addEventListener('drop',d,0);
function d(e){const dt=e.dataTransfer,files=dt.files;handleFiles(files)}
fileInputBtn.addEventListener('click',()=>fileInput.click());
fileInput.addEventListener('change',()=>handleFiles(fileInput.files));
function handleFiles(files){if(files.length===0)return;progressContainer.style.display='block';fileList.style.display='block';Array.from(files).forEach(f=>uploadFile(f))}
async function uploadFile(file){const fileId=crypto.randomUUID(),fileSize=file.size,fileName=file.name;
fileNameEl.textContent=fileName;fileSizeEl.textContent=formatFileSize(fileSize);statusText.textContent='Uploading...';
const fileItem=document.createElement('div');fileItem.className='file-item';fileItem.innerHTML='<div><strong>'+fileName+'</strong><br><span style="color:var(--text-muted);font-size:0.875rem">'+formatFileSize(fileSize)+'</span></div><div style="color:var(--text-muted);">Pending...</div>';fileList.appendChild(fileItem);
try{const fd=new FormData();fd.append('file',file);const r=await fetch('/api/upload',{method:'POST',body:fd}),result=await r.json();
if(result.success){fileItem.innerHTML='<div><strong>'+fileName+'</strong><br><span style="color:var(--text-muted);font-size:0.875rem">'+formatFileSize(fileSize)+'</span></div><div style="color:var(--success);">✓ Complete</div>';statusText.textContent='Upload complete!'}else throw new Error(result.error||'Upload failed')}catch(e){fileItem.innerHTML='<div><strong>'+fileName+'</strong><br><span style="color:var(--text-muted);font-size:0.875rem">'+formatFileSize(fileSize)+'</span></div><div style="color:var(--danger);">✗ Failed</div>';statusText.textContent='Upload failed'}}
function formatFileSize(b){if(b<1024)return b+' bytes';if(b<1024*1024)return(b/1024).toFixed(2)+' KB';return(b/(1024*1024)).toFixed(2)+' MB'}
</script></body></html>
      `;
      return new Response(html, { headers: { 'Content-Type': 'text/html' } });
    }
    return new Response('Not found', { status: 404 });
  },
};
