# beismoshiach.org — how to publish & update this site

This folder IS the website. Publishing works through **GitHub Desktop → Netlify**.
Once set up, updating the live site is a single button click. No zipping, no dragging.

## One-time setup (about 15 minutes)

### 1. Install GitHub Desktop
Download from https://desktop.github.com and install. Sign in (make a free
GitHub account if you don't have one).

### 2. Turn this folder into a repository
- In GitHub Desktop: **File → Add Local Repository**.
- Choose this folder.
- If it says "this isn't a Git repository," click **"create a repository"** — accept the defaults, click **Create Repository**.

### 3. Publish it to GitHub
- Click **Publish repository** (top bar).
- Keep **"Keep this code private"** checked.
- Click **Publish repository**. (The first upload takes a while — it's ~600 MB. Let it finish.)

### 4. Connect Netlify to the repo
- Go to https://app.netlify.com → your **beismoshiach** team.
- **Add new site → Import an existing project → GitHub**.
- Authorize, then pick the repository you just published.
- Build settings: leave **build command empty**, set **publish directory** to `.` (a single dot). Click **Deploy**.
- When it finishes, set your domain (beismoshiach.org) to this site under **Domain settings** (your DNS is already on Netlify).

That's it — the site is live.

## Updating the site later (the easy part)
Whenever the site files change (new articles, fixes from Claude, etc.):
1. Put the changed files into this folder.
2. Open **GitHub Desktop** — it shows what changed.
3. Type a short note in the **Summary** box (e.g. "add Hebrew fixes").
4. Click **Commit to main**, then **Push origin**.
Netlify rebuilds the live site automatically in ~1 minute. Done.

## Notes
- Images live in the `storage/` folder. Missing ones fill in when you run the image
  fetch script and drop the results into `storage/`.
- The `_redirects` and `netlify.toml` files configure Netlify — leave them as-is.
