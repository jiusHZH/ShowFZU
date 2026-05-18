# FZU Campus Community Requirements

## 1. Product Overview

This project is an English-language campus life showcase and community website for Fuzhou University. It combines public campus storytelling with lightweight community interaction.

The site should help users:

- Browse FZU campus stories, places, activities, study spaces, food, sports, and memories.
- Search and filter campus posts.
- Register and log in with a custom account system.
- Publish text, image, and video posts.
- Like, favorite, and comment on posts.
- Manage their public profile and private activity records.
- Visit a high-quality static official FZU introduction page.

The site is not only a normal forum. It should express digital storytelling and media convergence through text, images, videos, categories, and comments.

## 2. Language Policy

- The website interface must use English.
- Default demo data must use English.
- Real user posts are not strictly language-validated.
- The product should encourage English posting through UI copy and examples.

## 3. User Roles

The MVP supports only:

- Guest
- Registered User

There is a backend service, but there is no admin role and no admin console in the MVP.

## 4. Public And Private Access

Guests can publicly browse:

- Home page
- Category pages
- Search result pages
- Post detail pages
- Public author pages
- Official FZU Introduction page

Guests cannot:

- Create posts
- Like posts
- Favorite posts
- Comment or reply
- Access their own profile area
- Access private user pages such as My Posts, My Favorites, My Likes, profile editing, or password change

When a guest triggers a restricted action, the app redirects to the login page and preserves the return URL. After login, the user returns to the original page, but the interrupted action is not automatically executed.

## 5. Account Model

Each user has two identifiers:

- Account ID
- Username

Account ID rules:

- Required during registration.
- 8 to 12 digits.
- Pure numeric format.
- Globally unique.
- Immutable after registration.
- Can be used as a login name.
- Used for password recovery.
- Only visible to the account owner in account settings or profile management.
- Never shown on public pages.

Username rules:

- Required during registration.
- Globally unique.
- Editable after registration.
- Old username is released immediately after a successful change and can be used by another user.
- Can be used as a login name.
- Publicly displayed as the user's name.
- Allows letters, numbers, and spaces.
- Length: 2 to 30 characters.

Historical content display:

- If a user changes username or avatar, all past posts and comments display the new username and new avatar in real time.

## 6. Authentication

Registration requires:

- Account ID
- Username
- Password
- Confirm password
- Custom security question
- Security answer

Registration does not require:

- Avatar upload
- Bio

Login:

- Uses an explicit login method selector with two modes: `Account ID` and `Username`.
- The selector should be shown above the login identifier field, similar to a tab or segmented control.
- In `Account ID` mode, the identifier field accepts the immutable 8 to 12 digit Account ID.
- In `Username` mode, the identifier field accepts the editable public username.
- This explicit selector is required because usernames may contain only digits and can otherwise overlap with Account ID format.
- Password is entered separately.

Password policy:

- At least 8 characters.
- Must contain letters and numbers.

Session policy:

- HTTP-only cookie session.
- Frontend does not directly hold a token.
- Session duration: 7 days.
- Logout clears the session immediately.

Password recovery:

- User enters Account ID.
- User answers their custom security question.
- After verification, user can reset password.

Password change:

- Available in the private profile area.
- Requires old password, new password, and confirm new password.
- Must validate old password.
- Must validate that new password and confirm password match.

## 7. Profile And Author Pages

The product uses a public author page plus private management area.

Public author page:

- Accessible to guests.
- URL uses internal immutable user ID, such as `/users/u_8f3k2`.
- Shows username, avatar, bio, public posts, posts count, and total likes received.
- Does not show Account ID.
- Does not show collections count.
- Does not show likes count as a private behavior metric.

Private profile area:

- Only accessible to the logged-in owner.
- Shows avatar, username, bio, Account ID, posts count, favorites count, likes count, and account actions.
- Includes profile editing, password change, logout, My Posts, My Favorites, and My Likes.

Bio rules:

- Optional.
- Maximum 160 characters.

Avatar rules:

- Default avatar plus optional local image upload.
- Default avatar is generated from the username first letter.
- If the user has not uploaded an avatar, the generated avatar follows username changes.
- If the user has uploaded an avatar, the uploaded avatar remains after username changes.
- Upload formats: jpg, jpeg, png.
- Upload size limit: 2MB.

## 8. Navigation And Routing

Main navigation:

- Home
- Categories
- Create Post
- Profile

Search:

- Provided as a top global search box.
- Not a standalone nav item.

Frontend routing:

- Browser Router.
- Normal paths such as `/posts/p_123` and `/users/u_123`.

Core pages:

- Home
- Login
- Register
- Forgot Password
- Reset Password
- Create Post
- Edit Post
- Post Detail
- Search Results
- Categories
- Category Detail
- Public Author Page
- Private Profile
- My Posts
- My Favorites
- My Likes
- Edit Profile
- Change Password
- Official FZU Introduction

## 9. Home Page

The home page structure is:

- Top Hero / featured section
- Category cards
- Post feed
- Category filter tabs above the post feed

Home Hero:

- Static curated content.
- Uses an existing image from `resource/` as the background.
- Background should be a campus-wide atmosphere image.
- Introduces FZU campus architecture, scenery, and atmosphere.
- Includes multiple feature points such as Main Gate, Library, Fuyou Pavilion, and Campus Scenery.
- Feature points are clickable and route to category pages.
- Main Gate and Campus Scenery route to Campus Landmark.
- Library and Fuyou Pavilion route to Study Space.
- Includes a main button: `Explore Official FZU Guide`.
- The button routes to the Official FZU Introduction page.

Post feed:

- Default sorting: latest first by publish time.
- Shows title, cover, author, publish time, category, like count, favorite count, and media indicators.

Category entry:

- Home uses category cards.
- Post feed uses category tabs.

## 10. Official FZU Introduction Page

This is a fixed, high-quality static page.

Purpose:

- Present FZU through official-style architectural and campus photography.
- Use a photography exhibition style.
- Keep the page separate from user-generated content.

Entry:

- Home Hero main button, such as `Explore Official FZU Guide`.

Behavior:

- Fully static.
- No comments.
- No likes.
- No favorites.
- Not included in search indexing.

Content source:

- Current official guide source material lives in `resource/`.
- `FZU_Campus_Architecture.docx - 福州大学校园建筑Word文档.docx` is the primary official architecture text source.
- `照片（图书馆，卧龙桥，旋转楼梯，东门）.docx` is a supplemental official photo/text source for Library, Wolong Bridge, Qishan East Gate, and the Spiral Staircase.
- `FZU_Images_Collection.zip - 福州大学图片合集压缩包/fzu_images/` is the main reusable official image candidate folder.
- During development, parse the Word files and image folder into static JSON and asset files.
- At runtime, the page reads the processed static data and assets.

Official guide asset sufficiency:

- The source package is sufficient only when it contains at least one usable image for each official guide building item.
- It should also contain at least one distinct formal architectural image for the official guide hero.
- The home Hero image and official guide hero image must be different.
- Prefer having spare candidates for important buildings, but MVP can proceed with one strong image per building.
- Images without a matching English building name and introduction should be treated as visual candidates, not final official guide items.
- Current source material is sufficient for an MVP official guide page because it provides multiple official architecture/campus text entries and a reusable image candidate set.
- Any unreadable or corrupt image file must be excluded unless repaired. The current review found `building_6.jpg` and `campus_sunset.jpg` in the image collection unreadable in the local image decoder.
- Logo images can be used for branding accents, but they are not building/gallery candidates.

Visual direction:

- Photography exhibition page.
- Immersive large images.
- Restrained text.
- Strong visual rhythm.
- Top hero uses a formal architectural image.
- The official page hero image should be different from the home Hero image.

Page structure:

- Immersive top image.
- Building sections below.
- Each building section includes large image, English name, introduction, and spatial atmosphere.

Official guide image selection rules:

- Prioritize clear architectural subject, strong composition, natural light, and a calm official tone.
- Prefer high-resolution images suitable for large display; do not upscale low-resolution images to fake quality.
- Avoid images with visible watermarks, heavy compression, distracting text overlays, people as the main subject, messy indoor clutter, or unclear building identity.
- Prefer landscape or wide-croppable images for the hero and section lead visuals.
- Portrait images can be used in building sections when the subject benefits from vertical framing, but they should not be the only source for the page hero.
- If two images show the same building, choose the one with clearer structure, cleaner foreground, better sky or lighting, and more usable negative space for responsive cropping.

## 11. Categories

Each post has exactly one fixed primary category.

Supported categories:

- Campus Landmark
- Study Space
- Student Life
- Food and Cafe
- Sports and Leisure
- Digital Memory

Example category correction:

- Former `Library` example content is merged into `Study Space`.

Category descriptions:

- Each category has a fixed English curated short description.

Category pages:

- Include category header image.
- Include category description.
- Include posts in that category.
- Posts are sorted latest first.

Category imagery:

- Temporarily use fixed representative images from `resource/`.
- Select one representative image for each of the 6 categories.
- These images may be replaced later after the main features are complete.
- Category images should clearly match the category theme and remain readable when cropped into cards and page headers.
- Do not use official guide hero images as category images unless there are not enough distinct candidates.

## 12. Posts

Post detail URL:

- Uses internal immutable post ID, such as `/posts/p_7x9a2`.
- Title is not used in the URL.

Post creation:

- Available only to logged-in users.
- Posts are immediately public after creation.
- No admin review.
- No drafts in MVP.

Post required fields:

- Title is required.
- Category is required.
- At least one of body, images, or video is required.

Post optional fields:

- Body
- Images
- Video

Post editing:

- Users can edit their own posts.
- Editable fields include title, body, category, and media.
- Media editing supports deleting individual images, adding images, replacing video, deleting video, and changing image order.
- After media changes, cover is recalculated.

Post deletion:

- Users can delete their own posts.
- Deletion is permanent.
- Associated comments, likes, favorites, and media records are removed.
- Associated Storage files are deleted.

My Posts:

- Shows only the logged-in user's posts.
- Sorted by publish time descending.
- Each item shows title, publish time, category, like count, favorite count, edit entry, and delete entry.

## 13. Media Rules

Supported post media:

- Multiple images.
- At most 1 video.
- Image-only posts are allowed.
- Video-only posts are allowed.
- Mixed image and video posts are allowed.

Image upload:

- Formats: png, jpg, jpeg, gif.
- No image count limit.
- Each image maximum size: 10MB.

Video upload:

- Formats: mp4, webm, ogg, mov.
- At most 1 video per post.
- Video maximum size: 100MB.
- No server-side transcoding in MVP.
- If video exceeds 100MB, tell user to compress it first.

Total post media size:

- Maximum total upload size per post: 200MB.

Cover rule:

- Automatic cover.
- If images exist, use the first image.
- If no image exists but video exists, use generated video thumbnail.
- If no media exists, use default cover.

Video thumbnail:

- Automatically capture the middle frame.
- Applies to uploaded user videos and built-in demo videos.

Post detail image display:

- Use carousel layout.
- Show one image at a time.
- Support previous and next navigation.
- Include count and lazy loading for large image sets.

Post card media preview:

- Shows automatic cover.
- Shows media indicators.
- If video exists, show video icon.
- If multiple images exist, show image count.
- If both exist, show both indicators.

## 14. Search And Filtering

Global search scope:

- Title
- Body
- Author username

Global search does not search:

- Category names
- Official FZU Introduction page

Category filtering:

- Categories have dedicated entry points and pages.
- Category filtering is separate from keyword search.

Default list sorting:

- Home feed: latest first.
- Category page: latest first.
- Search results: latest first.

## 15. Likes And Favorites

Likes:

- Logged-in users can like posts.
- Guests are redirected to login.
- A user cannot duplicate-like the same post.
- Like is toggleable. Clicking again cancels the like.

Favorites:

- Logged-in users can favorite posts.
- Guests are redirected to login.
- A user cannot duplicate-favorite the same post.
- Favorite is toggleable. Clicking again cancels the favorite.

My Likes:

- Shows posts liked by the user.
- Sorted by like operation time descending.

My Favorites:

- Shows posts favorited by the user.
- Sorted by favorite operation time descending.

Public author stats:

- Shows posts count.
- Shows total likes received.
- Does not show private likes or favorites behavior.

## 16. Comments

Comment model:

- Threaded comments with a maximum depth of 2.
- Level 1: main comments on a post.
- Level 2: replies to main comments.
- Replies cannot be replied to again.

Comment permissions:

- Logged-in users can comment and reply.
- Guests are redirected to login.
- Users can delete their own comments.
- Users cannot edit comments.

Comment deletion:

- Soft delete placeholder.
- Deleted comment displays `This comment has been deleted.`
- If a deleted main comment has replies, replies remain visible.

## 17. Demo Data

Initial demo data:

- Use only the existing content from documents in `resource/`.
- Target size is around 30 posts from existing material.
- Do not invent extra demo posts for category balancing at this stage.

Demo media:

- Demo data must follow the same upload rules as user content.
- Existing videos exceed the 100MB limit and must be compressed into Web versions before inclusion.

Current known videos:

- `Study_ Center.mp4`: about 125 seconds and 203MB.
- `Food_ Diary.mp4`: about 235 seconds and 383MB.

## 18. Feedback And Validation

The system should provide user-facing feedback for:

- Login
- Registration
- Logout
- Post creation
- Post editing
- Post deletion
- File upload
- Like
- Favorite
- Comment
- Reply
- Comment deletion
- Password reset
- Password change
- Profile editing

The system should show errors for:

- Wrong password
- Invalid account ID
- Duplicate account ID
- Duplicate username
- Invalid password strength
- Password confirmation mismatch
- Empty title
- Missing body/media content
- Missing category
- Invalid file type
- File too large
- Total post media too large
- Empty comment
- Unauthenticated restricted action
- Unauthorized edit or delete action

## 19. Responsive Design

The site must support:

- Desktop
- Tablet
- Mobile

Important responsive requirements:

- Home Hero should remain visually strong on mobile.
- Official FZU Introduction page should preserve photo quality and reading rhythm on mobile.
- Post carousel must be usable on mobile.
- Threaded comments should remain readable with depth limited to 2.
- Navigation should keep Home, Categories, Create Post, and Profile accessible.

## 20. Out Of Scope For MVP

The following are not included in MVP:

- Admin role.
- Admin console.
- Post approval workflow.
- Draft posts.
- Comment editing.
- Multi-video posts.
- Server-side video transcoding.
- Supabase Auth.
- Direct frontend write access to Supabase database or Storage.
- Search indexing for the Official FZU Introduction page.
- Likes, favorites, or comments for the Official FZU Introduction page.
