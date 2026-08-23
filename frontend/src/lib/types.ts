export interface User {
  id: number;
  username: string;
  role: string;
  language_preference: string;
  is_active: boolean;
}

export interface Media {
  id: number;
  uploader_id: number | null;
  uploader_name: string | null;
  filename: string;
  original_filename: string;
  file_hash: string;
  media_type: string;
  mime_type: string;
  storage_path: string;
  status: string;
  width: number | null;
  height: number | null;
  duration: number | null;
  lqip: string | null;
  thumbnail_path: string | null;
  optimized_path: string | null;
  view_count: number;
  reaction_count: number;
  comment_count: number;
  favorite_count: number;
  is_visible: boolean;
  created_at: string;
}

export interface Comment {
  id: number;
  media_id: number;
  user_id: number;
  username: string;
  content: string;
  created_at: string;
}

export interface ActivityEvent {
  id: number;
  event_type: string;
  user_id: number;
  username: string;
  media_id: number | null;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface GalleryResponse {
  items: Media[];
  has_more: boolean;
  next_offset: number | null;
}
