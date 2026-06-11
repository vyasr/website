# LinkedIn Developer App Setup and Token Rotation

This guide covers setting up the LinkedIn Developer App for the vyasrcom automated posting workflow and keeping the access token fresh.

---

## Prerequisites

You need a LinkedIn account and access to the `vyasr/website` GitHub repo settings.

---

## Step 1: Create a LinkedIn Page

LinkedIn requires a Company or Creator Page associated with any developer app, even if you're posting to your personal profile.

1. Go to [LinkedIn Pages](https://www.linkedin.com/company/setup/new/)
2. Create a page with your name or brand (e.g., "Vyas Ramasubramani Personal")
3. You only need to do this once. The page won't be used for posting, just app association.

---

## Step 2: Create the Developer App

1. Go to [https://developer.linkedin.com/](https://developer.linkedin.com/) and click **Create App**
2. Fill in:
   - **App name**: something like "vyasrcom automation"
   - **LinkedIn Page**: select the page you created in Step 1
   - **App logo**: upload any image (required)
3. Agree to the terms and create the app

---

## Step 3: Add Products

In the app dashboard, go to the **Products** tab and request access to both:

- **Share on LinkedIn** — grants the `w_member_social` scope needed for posting
- **Sign In with LinkedIn using OpenID Connect** — grants `openid` and `profile` scopes needed to get your Author URN

Both are usually approved instantly.

> **Note**: You need *both* products. `w_member_social` alone won't let you retrieve your person ID, and without the OIDC product you can't reliably get your Author URN.

---

## Step 4: Configure OAuth 2.0

In the app dashboard, go to the **Auth** tab.

1. Under **OAuth 2.0 Settings**, add this redirect URL:
   ```
   https://localhost:3000/callback
   ```
2. Save changes
3. Note your **Client ID** and **Client Secret** from this tab. You'll need them in the next steps.

---

## Step 5: Obtain an Access Token

LinkedIn uses the OAuth 2.0 Authorization Code flow.

### 5a. Build the authorization URL

Construct this URL, replacing `YOUR_CLIENT_ID`:

```
https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id=YOUR_CLIENT_ID&redirect_uri=https://localhost:3000/callback&scope=w_member_social%20openid%20profile
```

Open it in your browser and click **Allow**.

You'll be redirected to `https://localhost:3000/callback?code=...` — the page won't load, and that's fine. Copy the `code` parameter value from the URL bar.

### 5b. Exchange the code for a token

```bash
curl -X POST https://www.linkedin.com/oauth/v2/accessToken \
  --data-urlencode "grant_type=authorization_code" \
  --data-urlencode "code=YOUR_AUTH_CODE" \
  --data-urlencode "client_id=YOUR_CLIENT_ID" \
  --data-urlencode "client_secret=YOUR_CLIENT_SECRET" \
  --data-urlencode "redirect_uri=https://localhost:3000/callback"
```

> **Critical**: Use `--data-urlencode` for every field, NOT `-d`. LinkedIn client secrets contain `==` characters that must be URL-encoded. Using `-d` will cause a cryptic auth error even with correct credentials.

The response looks like:

```json
{
  "access_token": "AQX...",
  "expires_in": 5183944,
  "id_token": "eyJ...",
  ...
}
```

Save both `access_token` and `id_token`.

---

## Step 6: Get Your Author URN

Your Author URN is `urn:li:person:<ID>` where `<ID>` comes from the `id_token`.

The `id_token` is a JWT. Decode the payload (middle section):

```bash
echo "YOUR_ID_TOKEN" | cut -d'.' -f2 | base64 -d 2>/dev/null
```

Find the `sub` field in the JSON output. That's your person ID.

Your Author URN is:

```
urn:li:person:<sub>
```

> **Note**: The `/v2/userinfo` endpoint sometimes returns 403 even with the correct scopes configured. The JWT decode approach above is more reliable and doesn't require an extra API call.

---

## Step 7: Store GitHub Secrets

In the `vyasr/website` repo, go to **Settings > Secrets and variables > Actions** and add:

| Secret name | Value |
|---|---|
| `LINKEDIN_ACCESS_TOKEN` | The `access_token` from Step 5 |
| `LINKEDIN_AUTHOR_URN` | `urn:li:person:<sub>` from Step 6 |

---

## Step 8: Token Rotation

Access tokens expire after **60 days**.

Set a calendar reminder for ~55 days after each token issuance.

When the token expires:

1. Repeat Steps 5 and 6 to get a new auth code, exchange it for a fresh token, and decode the new `id_token`
2. Update `LINKEDIN_ACCESS_TOKEN` in GitHub Secrets (the URN won't change, so `LINKEDIN_AUTHOR_URN` can stay)

**You don't need to recreate the app.** The Client ID and Client Secret stay the same indefinitely.

> **Note**: When a token expires, the `linkedin-post` CI job will fail with exit code 1. The deploy itself still succeeds since the LinkedIn posting step is non-blocking. You'll see a failed job in the Actions tab as the signal to rotate.

---

## Step 9: Verify the Setup (Optional)

Test the token by posting a draft (not publicly visible):

```bash
curl -s -o /dev/null -w "%{http_code}" \
  -X POST https://api.linkedin.com/rest/posts \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Linkedin-Version: 202601" \
  -H "X-Restli-Protocol-Version: 2.0.0" \
  -H "Content-Type: application/json" \
  -d '{
    "author": "YOUR_AUTHOR_URN",
    "commentary": "Test post",
    "visibility": "CONNECTIONS",
    "distribution": {"feedDistribution": "NONE"},
    "lifecycleState": "DRAFT"
  }'
```

A `201` response means everything is working.

After testing, go to your LinkedIn profile's **Activity** tab and delete any draft posts you created.
