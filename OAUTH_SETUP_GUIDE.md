# Google OAuth Setup Guide for Jal Sarovar
# Production Environment Configuration

---

## Step 1: Access Google Cloud Console

1. Go to: **https://console.cloud.google.com/**
2. Sign in with your Google account

---

## Step 2: Create or Select a Project

### Option A: Create New Project

1. Click the project dropdown at the top of the page
2. Click **"NEW PROJECT"**
3. Enter project details:
   - **Project name**: `Jal Sarovar Production`
   - **Organization**: Leave as default (optional)
4. Click **"CREATE"**
5. Wait for the project to be created (~30 seconds)
6. Select your new project from the dropdown

### Option B: Use Existing Project

1. Click the project dropdown
2. Select your existing project

---

## Step 3: Enable Google+ API

1. In the left sidebar, go to **"APIs & Services"** → **"Library"**
2. Search for: `Google+ API` or `People API`
3. Click on **"Google+ API"**
4. Click **"ENABLE"**
5. Wait for the API to be enabled

---

## Step 4: Configure OAuth Consent Screen

1. Go to **"APIs & Services"** → **"OAuth consent screen"**

2. **Check Current Status:**

   **If you see "User Type" selection:**
   - Select **"External"** (for public users)
   - Click **"CREATE"**

   **If you see an existing OAuth consent screen:**
   - Your project already has a consent screen configured
   - Click **"EDIT APP"** to modify it
   - Skip to step 3 below

   **If you see "Publishing status: Testing":**
   - This is normal for new apps
   - Click **"EDIT APP"** to review/modify settings
   - Skip to step 3 below

3. **Fill in App Information:**
   ```
   App name: Jal Sarovar Water Quality Monitoring
   User support email: [your-email@domain.com]
   App logo: (Optional - upload your logo)
   ```

4. **Application home page:**
   ```
   https://jalsarovar.com
   ```

5. **Application privacy policy link:**
   ```
   https://jalsarovar.com/privacy
   ```

6. **Application terms of service link:**
   ```
   https://jalsarovar.com/terms
   ```

7. **Authorized domains:**
   ```
   jalsarovar.com
   ```

8. **Developer contact information:**
   ```
   Email: [your-email@domain.com]
   ```

9. Click **"SAVE AND CONTINUE"**

10. **Scopes:**
    - Click **"ADD OR REMOVE SCOPES"**
    - Search and select:
      - `openid`
      - `email`
      - `profile`
    - Click **"UPDATE"**
    - Click **"SAVE AND CONTINUE"**

11. **Test users:** (Optional - for testing mode)
    - Add your email and test users
    - Click **"SAVE AND CONTINUE"**

12. **Summary:**
    - Review your settings
    - Click **"BACK TO DASHBOARD"**

---

## Step 5: Create OAuth 2.0 Credentials

1. Go to **"APIs & Services"** → **"Credentials"**

2. Click **"+ CREATE CREDENTIALS"** at the top

3. Select **"OAuth client ID"**

4. **Application type:**
   - Select: **"Web application"**

5. **Name:**
   ```
   Jal Sarovar Production
   ```

6. **Authorized JavaScript origins:**
   Click **"+ ADD URI"** and add:
   ```
   https://jalsarovar.com
   ```

   Click **"+ ADD URI"** again and add:
   ```
   https://www.jalsarovar.com
   ```

7. **Authorized redirect URIs:**
   Click **"+ ADD URI"** and add:
   ```
   https://jalsarovar.com/auth/google/callback
   ```

   Click **"+ ADD URI"** again and add:
   ```
   https://www.jalsarovar.com/auth/google/callback
   ```

8. Click **"CREATE"**

---

## Step 6: Copy Your Credentials

A popup will appear with your credentials:

```
Your Client ID:
123456789012-abcdefghijklmnopqrstuvwxyz123456.apps.googleusercontent.com

Your Client Secret:
GOCSPX-abcdefghijklmnopqrstuvwxyz
```

**IMPORTANT:**
- Click **"DOWNLOAD JSON"** to save a backup
- Copy both values - you'll need them in the next step

---

## Step 7: Update Your .env File

SSH into your server and edit the `.env` file:

```bash
cd /var/www/jalsarovar
sudo nano .env
```

Find and update these lines:

```bash
# Google OAuth
GOOGLE_CLIENT_ID=YOUR_CLIENT_ID_HERE.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=YOUR_CLIENT_SECRET_HERE
OAUTHLIB_INSECURE_TRANSPORT=0
```

**Replace with your actual values:**

```bash
# Google OAuth
GOOGLE_CLIENT_ID=123456789012-abcdefghijklmnopqrstuvwxyz123456.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-abcdefghijklmnopqrstuvwxyz
OAUTHLIB_INSECURE_TRANSPORT=0
```

**Important Notes:**
- `OAUTHLIB_INSECURE_TRANSPORT=0` MUST be 0 for production (HTTPS required)
- Never commit this file to Git
- Keep your Client Secret secure

Save and exit: `Ctrl+X`, then `Y`, then `Enter`

---

## Step 8: Verify File Permissions

```bash
sudo chown www-data:www-data /var/www/jalsarovar/.env
sudo chmod 640 /var/www/jalsarovar/.env
```

---

## Step 9: Restart Application

```bash
sudo supervisorctl restart jalsarovar
```

Wait 3 seconds, then verify:

```bash
sudo supervisorctl status jalsarovar
```

Should show: `RUNNING`

---

## Step 10: Test OAuth Login

1. Open your browser to: **https://jalsarovar.com/auth/login**

2. Click **"Sign in with Google"** button

3. You should be redirected to Google's login page

4. **If you see an error "This app isn't verified":**
   - This is normal for new OAuth apps
   - Click **"Advanced"**
   - Click **"Go to Jal Sarovar (unsafe)"**
   - This warning only shows to you during testing
   - To remove it, you need to verify your app (see Step 11)

5. Select your Google account

6. Allow permissions:
   - See your email address
   - See your personal info
   - Click **"Allow"**

7. You should be redirected back to: **https://jalsarovar.com/dashboard**

8. Verify you're logged in with your Google account

---

## Step 11: Verify Your App (Remove "Unverified App" Warning)

**Only needed if you want to remove the "This app isn't verified" warning:**

1. Go to **OAuth consent screen** in Google Cloud Console

2. Click **"PUBLISH APP"**

3. Click **"CONFIRM"**

4. **For verification (optional but recommended):**
   - Click **"PREPARE FOR VERIFICATION"**
   - Follow the verification process
   - Google will review your app (can take 1-2 weeks)
   - Verification is required if you exceed 100 users

**Note:** For internal testing and small user bases, you can keep the app in "Testing" mode and add specific test users.

---

## Step 12: Production Checklist

Verify all OAuth settings:

- [ ] Google Cloud project created
- [ ] Google+ API enabled
- [ ] OAuth consent screen configured
- [ ] OAuth 2.0 credentials created
- [ ] Authorized JavaScript origins include: `https://jalsarovar.com`
- [ ] Redirect URIs include: `https://jalsarovar.com/auth/google/callback`
- [ ] `.env` file updated with Client ID and Secret
- [ ] `OAUTHLIB_INSECURE_TRANSPORT=0` set
- [ ] Application restarted
- [ ] "Sign in with Google" tested and working

---

## Troubleshooting

### Error: "redirect_uri_mismatch"

**Problem:** The redirect URI doesn't match Google's configuration

**Solution:**
1. Check the URL in the error message
2. Go to Google Cloud Console → Credentials
3. Edit your OAuth client
4. Ensure the exact URL is in **Authorized redirect URIs**
5. Common mistake: Missing `www.` subdomain

### Error: "invalid_client"

**Problem:** Client ID or Secret is incorrect

**Solution:**
1. Re-copy Client ID and Secret from Google Cloud Console
2. Check for extra spaces in `.env` file
3. Ensure no quotes around the values

### Error: "This app isn't verified"

**Problem:** App is in testing mode

**Solution:**
- **Option 1:** Click "Advanced" → "Go to Jal Sarovar (unsafe)" during testing
- **Option 2:** Add test users to OAuth consent screen
- **Option 3:** Submit app for verification (for production with 100+ users)

### OAuth works locally but not in production

**Problem:** `OAUTHLIB_INSECURE_TRANSPORT` setting

**Solution:**
- Development (HTTP): `OAUTHLIB_INSECURE_TRANSPORT=1`
- Production (HTTPS): `OAUTHLIB_INSECURE_TRANSPORT=0`

---

## Security Best Practices

1. **Keep Client Secret secure:**
   - Never commit to Git
   - Don't share publicly
   - Rotate if compromised

2. **Use environment-specific credentials:**
   - Different Client ID/Secret for dev vs production
   - Prevents accidental production logins in development

3. **Monitor OAuth usage:**
   - Check Google Cloud Console for usage stats
   - Review which users are logging in
   - Monitor for suspicious activity

4. **Limit scopes:**
   - Only request `openid`, `email`, `profile`
   - Don't request unnecessary permissions

---

## Next Steps

After OAuth is configured:
1. Test registration with Google account
2. Test login with existing Google account
3. Verify email is auto-verified for OAuth users
4. Test role approval workflow
5. Configure email service (see EMAIL_SETUP_GUIDE.md)

---

**OAuth Setup Complete!** ✅

Your Jal Sarovar application now supports Google OAuth authentication.
