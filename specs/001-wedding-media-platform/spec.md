# Feature Specification: Wedding Media Platform

**Feature Branch**: `001-wedding-media-platform`

**Created**: 2026-07-04

**Status**: Draft

**Input**: User description: "A private, password-protected web app for collecting and sharing photos/videos from a single wedding (~150 guests), with real-time engagement, PWA support, and trilingual UI (EN / 中文 / Русский), deployed for reliable mainland-China access."

## User Scenarios & Testing *(mandatory)*

The platform serves two actors:

- **Guest** — a wedding attendee who uploads media, browses the gallery, reacts,
  comments, favorites, shares, and downloads.
- **Admin** — the couple or a helper. Can do everything a guest can, plus moderation,
  user management, statistics, and data export.

### User Story 1 - Guest Access & Authentication (Priority: P1)

A guest opens the site, enters a display name and the shared event password on a single
screen, and is admitted. Their account is created automatically on first entry and
reused on subsequent entries with the same name. Sessions stay alive silently while the
guest browses.

**Why this priority**: Nothing else in the platform is reachable without access. This is
the gate every other story depends on, and it embodies the frictionless-onboarding
principle.

**Independent Test**: Enter a brand-new display name with the correct event password →
land in the app with an active session. Re-enter the same name → same account. Enter a
wrong event password → rejected.

**Acceptance Scenarios**:

1. **Given** the event password is set, **When** a guest submits a new display name with
   the correct password, **Then** a guest account is created and the guest is admitted
   with an active session.
2. **Given** a guest "Anna" already exists, **When** someone enters "Anna" with the
   correct password, **Then** the existing account is returned (no duplicate).
3. **Given** the event password is set, **When** a guest submits the wrong password,
   **Then** access is refused and no account is created.
4. **Given** an admitted guest whose short-lived session has elapsed, **When** they keep
   browsing within the longer session window, **Then** access continues without a
   re-login prompt.
5. **Given** a guest chooses to log out, **When** logout completes, **Then** all of that
   guest's active sessions are ended.

---

### User Story 2 - Media Upload with Deduplication (Priority: P1)

A guest selects or drag-and-drops photos and videos and watches per-file and overall
progress as they upload. Identical files already on the platform are recognized and not
stored twice. After upload, each item is automatically prepared for fast display.

**Why this priority**: Collecting guests' media is the core purpose of the platform;
without upload there is nothing to browse or share.

**Independent Test**: Upload a new photo → it appears as processing then ready. Upload
the exact same file again → told it already exists, not re-stored. Attempt an
over-limit or disallowed file → rejected with a clear reason.

**Acceptance Scenarios**:

1. **Given** a guest selects several valid photos/videos, **When** they upload, **Then**
   each file shows individual progress and a combined total, and all succeed.
2. **Given** a file whose content already exists on the platform, **When** the guest
   uploads it, **Then** they are told it already exists and no duplicate is stored.
3. **Given** an image larger than the image size limit or a video larger than the video
   size limit, **When** the guest attempts upload, **Then** it is rejected with a clear
   size message.
4. **Given** a file of a disallowed type, **When** the guest attempts upload, **Then** it
   is rejected before any storage occurs.
5. **Given** a successful upload, **When** background preparation completes, **Then** the
   item has a thumbnail, an optimized version, a blurred placeholder, and (for videos) a
   known duration, and its status becomes ready.
6. **Given** uploads have been globally paused (archive mode), **When** a guest attempts
   to upload, **Then** the attempt is refused with an "uploads closed" message.

---

### User Story 3 - Gallery Browsing & Discovery (Priority: P1)

A guest browses an infinite-scroll gallery of all ready media, filters and sorts it,
searches by filename, and opens any item full-screen with navigation, download, and a
"similar photos" suggestion strip.

**Why this priority**: Viewing the collected memories is the primary payoff for guests
and completes the minimal usable product together with access and upload.

**Independent Test**: Load the gallery → media appears with lazy loading. Apply a filter
and a sort → results update accordingly. Open an item → full-screen view with next/prev
and a similar-items strip.

**Acceptance Scenarios**:

1. **Given** ready media exists, **When** a guest scrolls the gallery, **Then** items
   load progressively with placeholders while loading.
2. **Given** the gallery, **When** the guest filters by media type, uploader, or date
   range, or searches text, **Then** only matching items are shown.
3. **Given** the gallery, **When** the guest sorts by newest, oldest, most viewed, or
   most liked, **Then** ordering updates accordingly.
4. **Given** an item, **When** the guest opens it, **Then** a full-screen viewer offers
   image/video playback, keyboard/swipe navigation, download, and a strip of visually
   similar items.
5. **Given** an item hidden by an admin, **When** a guest browses or opens it directly,
   **Then** it is absent from the gallery and cannot be opened.

---

### User Story 4 - Social Engagement (Priority: P2)

A guest reacts to, comments on, and favorites media, and each view is counted. Reactions
are one-per-guest-per-item and toggle or switch type; guests can delete their own
comments.

**Why this priority**: Engagement makes the event feel alive and shared, but the
platform is still usable for its core purpose without it.

**Independent Test**: React to an item twice with the same type → net zero. Switch
reaction type → count stays exactly one. Add and delete own comment. Favorite an item →
appears in personal favorites.

**Acceptance Scenarios**:

1. **Given** an item, **When** a guest reacts with like/love/laugh, **Then** exactly one
   reaction is recorded for that guest on that item.
2. **Given** a guest already reacted, **When** they react again with the same type,
   **Then** the reaction is removed (net zero); **When** they react with a different
   type, **Then** the reaction is replaced (count remains one).
3. **Given** a guest's own comment, **When** they delete it, **Then** it is removed from
   view; an admin can delete any comment.
4. **Given** an item, **When** a guest favorites it, **Then** it appears in that guest's
   personal favorites list.
5. **Given** an item, **When** it is viewed, **Then** its view counter increments.

---

### User Story 5 - Sharing (Priority: P2)

A guest or admin creates a share link for the whole gallery or a single item, presented
with a QR code and a native share/copy option. Links track how often they are used and
can optionally expire.

**Why this priority**: Sharing broadens reach and is highly valued, but is secondary to
capturing and viewing media.

**Independent Test**: Generate a gallery share link → open it → reach the shared view;
access count increments. Generate a single-item link with an expiry → after expiry it no
longer grants access.

**Acceptance Scenarios**:

1. **Given** the gallery or a single item, **When** a user generates a share link,
   **Then** they receive a link, a QR code, and native-share/copy options.
2. **Given** a share link, **When** it is opened, **Then** its access count increments.
3. **Given** a share link with an expiry, **When** the expiry has passed, **Then** the
   link no longer grants access.

---

### User Story 6 - Real-Time & Notifications (Priority: P2)

Guests see live toasts as new uploads, reactions, and comments happen, can review a
recent-activity feed, and can opt in to web-push notifications. Optional email
notifications are available when email is configured.

**Why this priority**: Real-time buzz strongly enhances the live-event feel but is not
required for the platform to fulfill its core purpose.

**Independent Test**: With two sessions open, act in one → a live toast appears in the
other and the activity feed lists the event. Subscribe to push → receive a test push;
unsubscribe → stop receiving.

**Acceptance Scenarios**:

1. **Given** two active sessions, **When** one uploads/reacts/comments, **Then** the
   other receives a live toast promptly.
2. **Given** recent activity, **When** a guest opens the activity feed, **Then** it lists
   recent new-upload, new-reaction, new-comment, and new-favorite events.
3. **Given** a guest subscribes to push notifications, **When** a relevant event occurs,
   **Then** they receive a push; **When** they unsubscribe, **Then** delivery stops.
4. **Given** email delivery is not configured, **When** events occur, **Then** no email
   is attempted and nothing fails.

---

### User Story 7 - Progressive Web App Experience (Priority: P2)

A guest installs the site to their home screen, continues to browse cached content when
connectivity drops, and sees images blur-up smoothly as they load.

**Why this priority**: Reliability on phones over patchy venue wifi is a core principle,
but the platform still functions online without installability.

**Independent Test**: Load the site → prompted to install; install it → launches
standalone. Go offline → previously viewed content remains available. Load images →
blurred placeholder resolves to full image.

**Acceptance Scenarios**:

1. **Given** a supported device, **When** the guest visits, **Then** they can install the
   app and launch it standalone from the home screen.
2. **Given** previously loaded content, **When** connectivity is lost, **Then** that
   content remains viewable offline.
3. **Given** images loading, **When** they render, **Then** a low-quality placeholder
   blurs up to the full image.

---

### User Story 8 - Admin Console (Priority: P2)

An admin views platform statistics, manages users, moderates media, and exports media
metadata. Guard rails prevent an admin from modifying or deleting their own admin
account.

**Why this priority**: Moderation and oversight protect the experience, but the platform
can run for a trusted guest list without heavy administration.

**Independent Test**: Open the admin dashboard → see totals and top items. Promote a
guest to admin, deactivate a user. Hide a media item → it disappears from the guest
gallery but remains in the admin list. Export media metadata to a file.

**Acceptance Scenarios**:

1. **Given** an admin, **When** they open the dashboard, **Then** they see totals (media,
   users, views, reactions, comments, storage used), media-by-type, media-by-status,
   uploads over the last 7 days, and the top items by views.
2. **Given** an admin, **When** they list users, **Then** they can search and paginate,
   promote a guest to admin, deactivate, or delete a user.
3. **Given** an admin, **When** they attempt to modify or delete their own admin account,
   **Then** the action is refused.
4. **Given** an admin, **When** they hide a media item, **Then** it is removed from the
   guest gallery and single-item view but still appears in the admin media list; showing
   it again restores it.
5. **Given** a non-admin, **When** they access any admin-only capability, **Then** it is
   refused.
6. **Given** an admin, **When** they export media metadata, **Then** they receive a
   downloadable file containing all media records.

---

### User Story 9 - Bulk Download (Priority: P3)

A guest multi-selects items in the gallery and downloads them together as a single
archive.

**Why this priority**: A convenience that adds real value for keepsakes, but the least
essential of the feature set.

**Independent Test**: Select several items → request a bulk download → receive a single
archive containing exactly those items.

**Acceptance Scenarios**:

1. **Given** several selected items, **When** the guest requests a bulk download, **Then**
   they receive one archive containing those items.

---

### Edge Cases

- A guest uploads a file that is corrupt or fails background preparation → the item is
  marked failed and does not appear as ready in the gallery.
- Two guests choose the same display name → the same account is shared (documented
  behavior of frictionless access, not an error).
- A guest loses connectivity mid-upload → in-progress files report failure and can be
  retried without creating duplicates.
- A share link's underlying item is later hidden or deleted → the link no longer exposes
  it.
- An admin deactivates a user who is currently active → that user's sessions stop
  granting access.
- Concurrent identical uploads race on the same content hash → only one copy is stored.

## Requirements *(mandatory)*

### Functional Requirements

**Access & Authentication (FR-AUTH)**

- **FR-001**: The system MUST admit a guest given only a display name and the correct
  shared event password, creating the account automatically on first use (get-or-create)
  and reusing it for the same name thereafter.
- **FR-002**: The system MUST reject access when the event password is incorrect and
  MUST NOT create an account in that case.
- **FR-003**: The system MUST NOT collect email or a per-user password and MUST NOT
  expose any self-service registration step.
- **FR-004**: The system MUST maintain sessions with a short-lived access credential that
  is silently renewed by a longer-lived rotating credential, and logout MUST revoke all
  of a user's renewal credentials.
- **FR-005**: A renewal credential, once rotated, MUST NOT be reusable.

**Upload (FR-UPLOAD)**

- **FR-006**: Guests MUST be able to upload multiple photos and videos with per-file and
  aggregate progress feedback.
- **FR-007**: The system MUST detect duplicate content by a content hash and MUST report
  duplicates without storing them again.
- **FR-008**: The system MUST reject disallowed file types, images above the image size
  limit, and videos above the video size limit, with clear reasons.
- **FR-009**: After a successful upload the system MUST prepare, in the background, a
  thumbnail, an optimized version, a perceptual similarity fingerprint, a blurred
  placeholder, extracted capture metadata, and (for video) a duration.
- **FR-010**: The system MUST support a global switch that pauses all uploads (archive
  mode) and communicates this to guests.

**Gallery & Discovery (FR-GALLERY)**

- **FR-011**: The system MUST present ready media in an infinite-scroll gallery with lazy
  loading and loading placeholders.
- **FR-012**: Guests MUST be able to filter by media type, uploader, and date range, and
  search by filename text.
- **FR-013**: Guests MUST be able to sort by newest, oldest, most viewed, and most liked.
- **FR-014**: The system MUST provide a full-screen viewer with image display and video
  playback, keyboard and swipe navigation, download, and a strip of visually similar
  items.
- **FR-015**: The gallery and single-item views MUST exclude media that an admin has
  hidden.

**Social Engagement (FR-SOCIAL)**

- **FR-016**: The system MUST record at most one reaction (like, love, or laugh) per
  guest per item; reacting with the same type removes it and reacting with a different
  type replaces it.
- **FR-017**: Guests MUST be able to add comments and delete their own comments; admins
  MUST be able to delete any comment.
- **FR-018**: Guests MUST be able to favorite items into a personal favorites list.
- **FR-019**: The system MUST count views per item.

**Sharing (FR-SHARE)**

- **FR-020**: Users MUST be able to generate share links for the whole gallery or a
  single item, presented with a QR code and native-share/copy options.
- **FR-021**: The system MUST track each share link's access count and support an
  optional expiry after which the link no longer grants access.

**Real-Time & Notifications (FR-RT)**

- **FR-022**: The system MUST push live notifications of new uploads, reactions, and
  comments to connected clients.
- **FR-023**: The system MUST provide a recent-activity feed of new-upload, new-reaction,
  new-comment, and new-favorite events.
- **FR-024**: The system MUST support web-push subscribe/unsubscribe with a retrievable
  public key.
- **FR-025**: The system MUST support optional email notifications that are silently
  disabled when email is not configured.

**Progressive Web App (FR-PWA)**

- **FR-026**: The system MUST be installable to a device home screen and launch
  standalone.
- **FR-027**: The system MUST cache content via a service worker so previously loaded
  content remains available offline.
- **FR-028**: The system MUST render images with a low-quality placeholder that blurs up
  to the full image.

**Administration (FR-ADMIN)**

- **FR-029**: Admins MUST see dashboard statistics: totals (media, users, views,
  reactions, comments, storage used), media-by-type, media-by-status, uploads in the last
  7 days, and top items by views.
- **FR-030**: Admins MUST be able to list, search, and paginate users, promote a guest to
  admin, deactivate, and delete users.
- **FR-031**: The system MUST prevent an admin from modifying or deleting their own admin
  account.
- **FR-032**: Admins MUST be able to list all media including hidden, toggle visibility,
  and delete media; hidden media MUST never appear in guest views.
- **FR-033**: Admins MUST be able to export all media metadata to a downloadable file.
- **FR-034**: The system MUST refuse all admin-only capabilities to non-admin users.

**Bulk Operations (FR-BULK)**

- **FR-035**: Guests MUST be able to multi-select items and download them as a single
  archive.

**Cross-Cutting**

- **FR-036**: All user-facing text MUST be available in English, 中文, and Русский with
  full parity.
- **FR-037**: All content MUST be reachable only behind the shared event password; the
  site MUST NOT be publicly indexable.
- **FR-038**: The system MUST expose a health signal reflecting the availability of its
  core dependencies.

### Key Entities *(include if feature involves data)*

- **User**: A guest or admin, identified by a unique display name, with a role
  (guest/admin), a language preference (en/zh/ru), and an active/inactive flag.
- **Renewal Credential**: A rotating session-renewal token bound to a user, with an
  expiry and a revoked flag.
- **Media Item**: An uploaded photo or video, content-addressed by a unique hash, with
  original and derived representations (thumbnail, optimized, blurred placeholder),
  dimensions/duration, capture metadata, a similarity fingerprint, a view count, a
  processing status, and a visibility flag; owned by an uploader.
- **Reaction**: A single guest's reaction (like/love/laugh) to a media item; unique per
  guest per item.
- **Comment**: A guest's text comment on a media item, individually removable.
- **Favorite**: A guest's personal bookmark of a media item; unique per guest per item.
- **Share Link**: A token granting access to the gallery or a single item, with an
  access count and optional expiry, attributed to its creator.
- **Activity Event**: A record of a notable action (new upload/reaction/comment/favorite)
  for the activity feed and live notifications.
- **Push Subscription**: A user's registration to receive web-push notifications.
- **Event Configuration**: Singleton platform settings, including whether uploads are
  enabled, the size limits, and event name/date.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A first-time guest goes from the entry screen to browsing the gallery in no
  more than two inputs (display name + event password) and under 30 seconds.
- **SC-002**: Identical content is never stored more than once (0 duplicate stored files
  across the collection).
- **SC-003**: The platform serves 150 concurrent guests browsing and uploading without
  visible degradation.
- **SC-004**: 100% of user-facing strings render correctly in English, 中文, and Русский.
- **SC-005**: Hidden media never appears to guests (0 occurrences in guest gallery or
  direct-open across the event).
- **SC-006**: A guest can install the app and continue viewing previously loaded content
  with connectivity disabled.
- **SC-007**: A reaction is always at most one per guest per item, and switching type
  never increases the count beyond one.
- **SC-008**: New uploads, reactions, and comments appear to other connected guests as
  live notifications within a few seconds of the action.
- **SC-009**: Every capability restricted to admins is refused for non-admins in 100% of
  attempts.
- **SC-010**: The platform is deployed and smoke-tested in production on or before
  2026-09-15.

## Assumptions

- The platform serves a single wedding event (~150 guests); multi-event tenancy is out of
  scope.
- Guests access primarily from mobile devices on congested venue wifi within mainland
  China.
- ICP filing is being obtained and will be active before go-live.
- The shared event password is distributed to guests out of band (e.g., on the
  invitation); its secrecy is assumed adequate for a closed guest list.
- Reasonable industry-standard defaults apply where unspecified (data retention,
  user-friendly error messages, standard session security).
