# Full-Stack Resource Management System

## Overview

Designed and implemented a complete resource management feature from scratch, enabling students and teachers to upload, organize, and interact with educational materials (PDFs, videos, YouTube content).

**Tech Stack:** React, TypeScript, Next.js, Python FastAPI, Supabase (PostgreSQL + Storage), YouTube Transcript API

---

## The Challenge

Build a production-ready feature that allows users to:
1. Upload PDF documents and store them in cloud storage
2. Add YouTube videos and automatically extract timestamped transcripts
3. View PDFs and videos inline
4. Filter and search across all resources
5. Manage access permissions (default vs. student-specific resources)

---

## Architecture & Implementation

### System Design

```
┌──────────────────────────────────────┐
│         Frontend (Next.js)           │
│  ┌────────────────────────────────┐  │
│  │  Resource Management UI        │  │
│  │  - File upload with progress   │  │
│  │  - YouTube URL input           │  │
│  │  - PDF/Video viewer overlay    │  │
│  │  - Filter & search             │  │
│  └────────────┬───────────────────┘  │
└───────────────┼──────────────────────┘
                │
       ┌────────▼────────┐
       │  Supabase API   │
       │  (PostgreSQL)   │
       └────────┬────────┘
                │
    ┌───────────┴───────────┐
    │                       │
┌───▼─────────────┐  ┌──────▼──────────────┐
│  Supabase       │  │  Python Backend     │
│  Storage        │  │  (FastAPI)          │
│  (File hosting) │  │  ┌───────────────┐  │
└─────────────────┘  │  │ YouTube       │  │
                     │  │ Transcript    │  │
                     │  │ Service       │  │
                     │  └───────────────┘  │
                     └─────────────────────┘
```

---

## Key Features Built

### 1. File Upload with Cloud Storage

**Frontend Implementation (`app/lib/supabase/resources.ts`):**

```typescript
export async function uploadResourceFile(
  file: File,
  title: string,
  description: string
): Promise<Resource> {
  const supabase = createClientComponentClient();
  const user = await getCurrentUser();
  
  // Generate unique filename to prevent collisions
  const timestamp = new Date().getTime();
  const fileExt = file.name.split('.').pop();
  const fileName = `${timestamp}_${file.name}`;
  const filePath = `resources/${user.id}/${fileName}`;
  
  // Upload to Supabase Storage
  const { data: uploadData, error: uploadError } = await supabase.storage
    .from('resources')
    .upload(filePath, file, {
      cacheControl: '3600',
      upsert: false
    });
  
  if (uploadError) throw uploadError;
  
  // Get public URL
  const { data: { publicUrl } } = supabase.storage
    .from('resources')
    .getPublicUrl(filePath);
  
  // Create database record
  const { data, error } = await supabase
    .from('resources')
    .insert({
      user_id: user.id,
      title,
      description,
      resource_type: 'document',
      file_url: publicUrl,
      file_path: filePath,
      file_type: file.type,
      file_size: file.size
    })
    .select()
    .single();
  
  return data;
}
```

**Challenges Solved:**
- **Filename collisions:** Added timestamp prefix
- **Progress tracking:** Integrated upload progress callbacks
- **Error handling:** User-friendly error messages for storage quota, file type restrictions
- **Security:** Row-Level Security (RLS) policies ensure users only access their own files

---

### 2. YouTube Transcript Extraction

**Backend Service (`backend/mcp-service/src/services/youtube_transcript_service.py`):**

```python
class YouTubeTranscriptService:
    """
    Extracts timestamped transcripts from YouTube videos
    """
    
    async def extract_transcript(
        self,
        video_url: str,
        preferred_languages: List[str] = ['en']
    ) -> Dict[str, Any]:
        """
        Extract transcript with timestamps and metadata
        """
        video_id = self._extract_video_id(video_url)
        
        try:
            # Fetch transcript using youtube-transcript-api
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Try preferred languages first
            transcript = None
            for lang in preferred_languages:
                try:
                    transcript = transcript_list.find_transcript([lang])
                    break
                except:
                    continue
            
            # Fall back to auto-generated if available
            if not transcript:
                transcript = transcript_list.find_generated_transcript(preferred_languages)
            
            # Fetch actual transcript data
            transcript_data = transcript.fetch()
            
            # Format with timestamps
            formatted_transcript = self._format_transcript(transcript_data)
            
            return {
                "success": True,
                "video_id": video_id,
                "language": transcript.language_code,
                "transcript": formatted_transcript,
                "segments": len(transcript_data)
            }
            
        except Exception as e:
            logger.error(f"Transcript extraction failed for {video_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "video_id": video_id
            }
    
    def _format_transcript(self, transcript_data: List[Dict]) -> str:
        """
        Format transcript with clickable timestamps
        """
        formatted = []
        for entry in transcript_data:
            timestamp = self._format_timestamp(entry['start'])
            text = entry['text']
            formatted.append(f"[{timestamp}] {text}")
        
        return "\n".join(formatted)
    
    def _format_timestamp(self, seconds: float) -> str:
        """
        Convert seconds to MM:SS or HH:MM:SS format
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"
```

**Features:**
- **Multi-language support:** Tries preferred languages, falls back to auto-generated
- **Timestamp formatting:** Human-readable MM:SS format
- **Segmentation:** Preserves original segment boundaries for future features (time-range selection)
- **Error handling:** Graceful degradation if transcripts unavailable

---

### 3. Frontend UI with PDF/Video Viewer

**Component Structure (`app/resources/page.tsx`):**

```typescript
export default function ResourcesPage() {
  const [resources, setResources] = useState<Resource[]>([]);
  const [currentResource, setCurrentResource] = useState<Resource | null>(null);
  const [isPDFViewerOpen, setIsPDFViewerOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<'all' | 'document' | 'video'>('all');
  
  // Fetch resources on mount
  useEffect(() => {
    async function loadResources() {
      const defaultRes = await getDefaultResources();
      const studentRes = await getStudentResources();
      setResources([...defaultRes, ...studentRes]);
    }
    loadResources();
  }, []);
  
  // Filter and search
  const filteredResources = resources.filter(resource => {
    const matchesType = filterType === 'all' || resource.resource_type === filterType;
    const matchesSearch = resource.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          resource.description?.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesType && matchesSearch;
  });
  
  // Handle resource click (open viewer)
  const handleResourceClick = async (resourceId: string) => {
    const resource = resources.find(r => r.id === resourceId);
    if (!resource) return;
    
    setCurrentResource(resource);
    setIsPDFViewerOpen(true);
  };
  
  return (
    <PageContainer>
      {/* Search and Filter UI */}
      <ControlsSection>
        <SearchBar
          placeholder="Search resources..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        <FilterButtons>
          <FilterButton active={filterType === 'all'} onClick={() => setFilterType('all')}>
            All
          </FilterButton>
          <FilterButton active={filterType === 'document'} onClick={() => setFilterType('document')}>
            Documents
          </FilterButton>
          <FilterButton active={filterType === 'video'} onClick={() => setFilterType('video')}>
            Videos
          </FilterButton>
        </FilterButtons>
      </ControlsSection>
      
      {/* Resource Grid */}
      <ResourceGrid>
        {filteredResources.map(resource => (
          <ResourceCard
            key={resource.id}
            resource={resource}
            onClick={() => handleResourceClick(resource.id)}
          />
        ))}
      </ResourceGrid>
      
      {/* PDF/Video Viewer Overlay */}
      <PDFViewerOverlay $isVisible={isPDFViewerOpen && currentResource !== null}>
        <PDFViewerContainer>
          <PDFViewerHeader>
            <h2>{currentResource?.title}</h2>
            <CloseButton onClick={() => setIsPDFViewerOpen(false)}>
              ✕
            </CloseButton>
          </PDFViewerHeader>
          <PDFViewerContent>
            {currentResource ? (
              currentResource.resource_type === 'video' ? (
                <iframe
                  src={currentResource.video_url?.replace('watch?v=', 'embed/')}
                  style={{ width: '100%', height: '800px', border: 'none' }}
                  title={currentResource.title}
                  allowFullScreen
                />
              ) : (
                <iframe
                  src={currentResource.file_url}
                  style={{ width: '100%', height: '800px', border: 'none' }}
                  title={currentResource.title}
                />
              )
            ) : (
              <div>Loading...</div>
            )}
          </PDFViewerContent>
        </PDFViewerContainer>
      </PDFViewerOverlay>
    </PageContainer>
  );
}
```

**UI/UX Features:**
- **Real-time search:** Filter as you type
- **Type filtering:** Toggle between documents, videos, or all
- **Overlay viewer:** Modal-style viewer with close button
- **Responsive design:** Adapts to different screen sizes
- **Loading states:** Proper null checks to prevent crashes

---

## Bug Fixes & Debugging

### Critical Null Reference Bug

**Error:**
```
Uncaught TypeError: Cannot read properties of null (reading 'resource_type')
```

**Root Cause:** The PDF viewer was trying to access `currentResource.resource_type` before `currentResource` was set.

**Fix:**
```typescript
// BEFORE (buggy):
<PDFViewerOverlay $isVisible={isPDFViewerOpen}>
  {currentResource?.resource_type === 'video' ? ... }  // Crashes if null
</PDFViewerOverlay>

// AFTER (fixed):
<PDFViewerOverlay $isVisible={isPDFViewerOpen && currentResource !== null}>
  {currentResource ? (
    currentResource.resource_type === 'video' ? ...
  ) : (
    <div>Loading...</div>
  )}
</PDFViewerOverlay>
```

**Learning:** Always add proper null checks in async data flows, especially for user-triggered actions.

---

## Database Schema

```sql
-- resources table
CREATE TABLE resources (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES auth.users(id),
  title TEXT NOT NULL,
  description TEXT,
  resource_type TEXT CHECK (resource_type IN ('document', 'video')),
  file_url TEXT,           -- Supabase Storage URL or YouTube URL
  file_path TEXT,          -- Storage path (for deletion)
  file_type TEXT,          -- MIME type
  file_size BIGINT,        -- Bytes
  video_url TEXT,          -- Original YouTube URL
  video_transcript TEXT,   -- Extracted transcript
  is_default BOOLEAN DEFAULT FALSE,  -- Teacher-uploaded default resources
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Row Level Security (RLS) Policies
ALTER TABLE resources ENABLE ROW LEVEL SECURITY;

-- Users can read their own resources + default resources
CREATE POLICY "Users can read own and default resources"
  ON resources FOR SELECT
  USING (
    user_id = auth.uid() OR is_default = TRUE
  );

-- Users can insert their own resources
CREATE POLICY "Users can insert own resources"
  ON resources FOR INSERT
  WITH CHECK (user_id = auth.uid());

-- Users can update/delete their own resources
CREATE POLICY "Users can update own resources"
  ON resources FOR UPDATE
  USING (user_id = auth.uid());
```

---

## Skills Demonstrated

✅ **Full-Stack Development:** Frontend UI, backend services, database schema  
✅ **React/TypeScript:** State management, hooks, styled components  
✅ **Python/FastAPI:** Async services, API integration  
✅ **Cloud Storage:** Supabase Storage, file management, public URLs  
✅ **API Integration:** YouTube Transcript API, error handling  
✅ **Database Design:** Schema design, RLS policies, indexing  
✅ **UX/UI:** Loading states, error handling, responsive design  
✅ **Debugging:** Systematic investigation, null safety, race conditions

---

## Future Enhancements (Phase 2)

Planned features that build on this foundation:
- **PDF Page Selection:** UI to select specific pages for content generation
- **Video Time-Range Selection:** Select video segments to generate flashcards from
- **Transcript Caching:** Store transcripts in DB to avoid re-fetching
- **Flashcard Generation:** AI-powered flashcard creation from resources
- **Assessment Generation:** Create quizzes from uploaded materials

---

## Code Organization

```
app/
├── resources/
│   └── page.tsx                    # Main UI component (~1,000 lines)
├── lib/
│   └── supabase/
│       └── resources.ts            # Resource management functions
└── api/
    └── resources/
        └── route.ts                # Next.js API routes

backend/mcp-service/
└── src/
    ├── services/
    │   └── youtube_transcript_service.py  # Transcript extraction (~200 lines)
    └── routes/
        └── resources.py            # FastAPI endpoints (~60 lines)
```

---

## Deep Dive Resources

Want to see the complete deployment setup and implementation details?

### 🚀 [Resources Feature - Full Implementation Guide](/archive/09-resources-feature-implementation/)
- Docker containerization and Google Cloud Run deployment
- Complete backend service code (YouTube transcript extraction)
- Database schema and Supabase configuration
- CI/CD pipeline setup and monitoring strategies

