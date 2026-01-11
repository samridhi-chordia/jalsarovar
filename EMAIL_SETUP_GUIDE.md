# Email Service Setup Guide for Jal Sarovar
# SendGrid & SMTP Configuration with DNS Records

---

## Table of Contents

1. [SendGrid Setup (Recommended)](#sendgrid-setup-recommended)
2. [Gmail SMTP Setup (Development/Testing)](#gmail-smtp-setup-developmenttesting)
3. [DNS Records Configuration (SPF, DKIM, DMARC)](#dns-records-configuration)
4. [Testing Email Service](#testing-email-service)
5. [Troubleshooting](#troubleshooting)

---

# SendGrid Setup (Recommended)

**Best for:** Production, high deliverability, professional email

**Free tier:** 100 emails/day forever

---

## Step 1: Create SendGrid Account

1. Go to: **https://signup.sendgrid.com/**

2. Fill in registration:
   ```
   Email: your-email@domain.com
   Password: [secure password]
   Company Name: Jal Sarovar
   Website: jalsarovar.com
   ```

3. Verify your email address (check inbox)

4. Complete the setup questionnaire:
   - How will you send email? **Integration**
   - Language: **Python**
   - Are you a developer? **Yes**

---

## Step 2: Create API Key

1. After logging in, go to **Settings** → **API Keys**

2. Click **"Create API Key"**

3. Enter details:
   ```
   API Key Name: Jal Sarovar Production
   API Key Permissions: Full Access
   ```

4. Click **"Create & View"**

5. **IMPORTANT:** Copy the API key immediately:
   ```
   SG.xxxxxxxxxxxxxxxxxxxxxxxx.yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy
   ```

6. **Save it securely** - you won't be able to see it again!

---

## Step 3: Verify Sender Identity

### Option A: Single Sender Verification (Quick Start)

1. Go to **Settings** → **Sender Authentication** → **Single Sender Verification**

2. Click **"Create New Sender"**

3. Fill in sender details:
   ```
   From Name: Jal Sarovar
   From Email Address: noreply@jalsarovar.com
   Reply To: support@jalsarovar.com (optional)
   Company Address: [Your address]
   City: [Your city]
   State: [Your state]
   Zip Code: [Your zip]
   Country: India
   ```

4. Click **"Create"**

5. Check your email (`noreply@jalsarovar.com`) for verification link

6. Click the verification link

7. Wait for "Verified" status in SendGrid

### Option B: Domain Authentication (Recommended for Production)

*See Step 4 below for full domain authentication*

---

## Step 4: Authenticate Your Domain (Recommended)

**Benefits:**
- Higher deliverability
- Better sender reputation
- No "via sendgrid.net" label
- Professional appearance

### 4.1: Start Domain Authentication

1. Go to **Settings** → **Sender Authentication**

2. Click **"Authenticate Your Domain"**

3. Select your DNS provider:
   - **Cloudflare** (if using Cloudflare)
   - **GoDaddy**
   - **Namecheap**
   - Or select "Other"

4. Enter your domain:
   ```
   Domain: jalsarovar.com
   ```

5. **Advanced Settings:**
   ```
   Brand your links: Yes
   Use automated security: Yes
   ```

6. Click **"Next"**

### 4.2: Add DNS Records

SendGrid will provide DNS records. You need to add these to your domain's DNS settings.

**Example DNS records you'll receive:**

```
Type: CNAME
Host: em1234.jalsarovar.com
Value: u1234567.wl001.sendgrid.net

Type: CNAME
Host: s1._domainkey.jalsarovar.com
Value: s1.domainkey.u1234567.wl001.sendgrid.net

Type: CNAME
Host: s2._domainkey.jalsarovar.com
Value: s2.domainkey.u1234567.wl001.sendgrid.net
```

### 4.3: Add Records to Your DNS Provider

**For Cloudflare:**

1. Log in to Cloudflare
2. Select your domain: `jalsarovar.com`
3. Go to **DNS** → **Records**
4. Click **"Add record"** for each record:
   - Type: `CNAME`
   - Name: `em1234` (copy from SendGrid, remove `.jalsarovar.com`)
   - Target: `u1234567.wl001.sendgrid.net`
   - Proxy status: **DNS only** (gray cloud, not orange)
   - TTL: Auto
   - Click **"Save"**

5. Repeat for all CNAME records from SendGrid

**Important:** Set Proxy status to "DNS only" (gray cloud) for email DNS records!

### 4.4: Verify DNS Records

1. Wait 5-10 minutes for DNS propagation

2. Return to SendGrid

3. Click **"Verify"**

4. If successful: ✅ "Domain authenticated"

5. If failed: Wait longer or check DNS records

---

## Step 5: Update .env File

SSH into your server:

```bash
cd /var/www/jalsarovar
sudo nano .env
```

Update these lines:

```bash
# Email Configuration - SendGrid
MAIL_SERVER=smtp.sendgrid.net
MAIL_PORT=587
MAIL_USERNAME=apikey
MAIL_PASSWORD=SG.your-actual-sendgrid-api-key-here
MAIL_DEFAULT_SENDER=noreply@jalsarovar.com

# Site URL
SITE_URL=https://jalsarovar.com
```

**Important:**
- `MAIL_USERNAME` must be exactly `apikey` (not your SendGrid username)
- `MAIL_PASSWORD` is your SendGrid API key
- `MAIL_DEFAULT_SENDER` must match your verified sender

Save: `Ctrl+X`, `Y`, `Enter`

---

## Step 6: Restart Application

```bash
sudo supervisorctl restart jalsarovar
sudo supervisorctl status jalsarovar
```

Should show: `RUNNING`

---

# Gmail SMTP Setup (Development/Testing)

**Best for:** Development, testing, low volume

**Limitations:**
- 500 emails/day limit
- Less reliable deliverability
- May trigger spam filters

---

## Step 1: Enable 2-Factor Authentication

1. Go to: **https://myaccount.google.com/security**

2. Under "Signing in to Google", click **"2-Step Verification"**

3. Follow the setup wizard to enable 2FA

---

## Step 2: Generate App Password

1. Go to: **https://myaccount.google.com/apppasswords**

2. Sign in with your Gmail account

3. Select app: **"Mail"**

4. Select device: **"Other (Custom name)"**
   ```
   Name: Jal Sarovar Production
   ```

5. Click **"Generate"**

6. Copy the 16-character password:
   ```
   abcd efgh ijkl mnop
   ```

7. **Save it securely** - you won't see it again

---

## Step 3: Update .env File

```bash
cd /var/www/jalsarovar
sudo nano .env
```

Update these lines:

```bash
# Email Configuration - Gmail
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=abcdefghijklmnop
MAIL_DEFAULT_SENDER=noreply@jalsarovar.com

# Site URL
SITE_URL=https://jalsarovar.com
```

**Important:**
- Remove spaces from app password: `abcd efgh ijkl mnop` → `abcdefghijklmnop`
- Use your actual Gmail address for `MAIL_USERNAME`

Save: `Ctrl+X`, `Y`, `Enter`

---

## Step 4: Restart Application

```bash
sudo supervisorctl restart jalsarovar
```

---

# DNS Records Configuration

**Purpose:** Improve email deliverability and prevent emails from going to spam

**Required records:** SPF, DKIM, DMARC

---

## SPF (Sender Policy Framework)

**What it does:** Specifies which servers can send email from your domain

### For SendGrid:

Add this TXT record to your DNS:

```
Type: TXT
Name: @
Value: v=spf1 include:sendgrid.net ~all
```

### For Gmail:

```
Type: TXT
Name: @
Value: v=spf1 include:_spf.google.com ~all
```

### If using both (SendGrid + Gmail):

```
Type: TXT
Name: @
Value: v=spf1 include:sendgrid.net include:_spf.google.com ~all
```

---

## DKIM (DomainKeys Identified Mail)

**What it does:** Adds digital signature to verify email authenticity

### For SendGrid:

DKIM records are automatically added when you complete Step 4 (Domain Authentication).

The CNAME records you added include DKIM keys.

### For Gmail:

Gmail doesn't provide DKIM for custom domains. Use SendGrid for production.

---

## DMARC (Domain-based Message Authentication)

**What it does:** Tells receiving servers what to do with emails that fail SPF/DKIM

Add this TXT record:

```
Type: TXT
Name: _dmarc
Value: v=DMARC1; p=quarantine; rua=mailto:dmarc-reports@jalsarovar.com; pct=100; adkim=s; aspf=s
```

**Explanation:**
- `p=quarantine` - Put suspicious emails in spam
- `rua=mailto:...` - Send reports to this email
- `pct=100` - Apply policy to 100% of emails
- `adkim=s` - Strict DKIM alignment
- `aspf=s` - Strict SPF alignment

---

## How to Add DNS Records (Cloudflare Example)

1. Log in to **Cloudflare**

2. Select domain: `jalsarovar.com`

3. Go to **DNS** → **Records**

4. **Add SPF Record:**
   - Click **"Add record"**
   - Type: `TXT`
   - Name: `@`
   - Content: `v=spf1 include:sendgrid.net ~all`
   - TTL: `Auto`
   - Click **"Save"**

5. **Add DMARC Record:**
   - Click **"Add record"**
   - Type: `TXT`
   - Name: `_dmarc`
   - Content: `v=DMARC1; p=quarantine; rua=mailto:dmarc-reports@jalsarovar.com; pct=100`
   - TTL: `Auto`
   - Click **"Save"**

6. **DKIM Records:**
   - Already added during SendGrid domain authentication (Step 4.3)

---

## Verify DNS Records

Wait 10-15 minutes for DNS propagation, then verify:

### Check SPF:

```bash
dig TXT jalsarovar.com +short | grep spf
```

Should show: `"v=spf1 include:sendgrid.net ~all"`

### Check DMARC:

```bash
dig TXT _dmarc.jalsarovar.com +short
```

Should show: `"v=DMARC1; p=quarantine..."`

### Online Tools:

- **MXToolbox:** https://mxtoolbox.com/spf.aspx
- **DMARC Analyzer:** https://www.dmarcanalyzer.com/

---

# Testing Email Service

## Test 1: Python Test Script

```bash
cd /var/www/jalsarovar
source venv/bin/activate

python3 << 'EOF'
from app import create_app, mail
from flask_mail import Message

app = create_app('production')
with app.app_context():
    msg = Message(
        subject='Test Email from Jal Sarovar',
        recipients=['your-personal-email@gmail.com'],  # Your email
        body='This is a test email. If you receive this, email is working!',
        sender='noreply@jalsarovar.com'
    )

    try:
        mail.send(msg)
        print('✅ Email sent successfully!')
        print('Check your inbox (and spam folder)')
    except Exception as e:
        print(f'❌ Error sending email: {e}')
EOF
```

**Expected output:** `✅ Email sent successfully!`

Check your email inbox and spam folder.

---

## Test 2: Registration Email Verification

1. Go to: **https://jalsarovar.com/auth/register**

2. Fill in the registration form:
   - Use your personal email
   - Select a role

3. Submit the form

4. Check your email for verification link

5. Click the verification link

6. Should redirect to login page with success message

---

## Test 3: Password Reset Email

1. Go to: **https://jalsarovar.com/auth/forgot-password**

2. Enter your email address

3. Submit the form

4. Check email for password reset link

5. Click the link and set a new password

---

## Test 4: Role Approval Notification

*This requires admin access and a pending role approval*

1. Register a user with a restricted role (e.g., Field Collector)

2. Log in as admin

3. Go to: **https://jalsarovar.com/admin/role-requests**

4. Approve the role request

5. User should receive approval email

---

# Troubleshooting

## Email Not Sending

### Check 1: SMTP Credentials

```bash
# Verify .env file
cat /var/www/jalsarovar/.env | grep MAIL_
```

Should show your SMTP settings correctly.

### Check 2: Application Logs

```bash
sudo tail -50 /var/www/jalsarovar/logs/error.log | grep -i "mail\|smtp\|email"
```

Look for error messages.

### Check 3: SendGrid Dashboard

1. Log in to SendGrid
2. Go to **Activity**
3. Check if emails are being received by SendGrid
4. Look for bounces or blocks

---

## Emails Going to Spam

**Solutions:**

1. **Complete domain authentication** (SendGrid Step 4)

2. **Add all DNS records:**
   - SPF ✅
   - DKIM ✅
   - DMARC ✅

3. **Warm up your sending domain:**
   - Start with small volumes
   - Gradually increase
   - Maintain good reputation

4. **Improve email content:**
   - Avoid spam trigger words
   - Include unsubscribe link
   - Use proper HTML formatting

5. **Test with mail-tester.com:**
   - Send test email to: `test@mail-tester.com`
   - Visit: https://www.mail-tester.com
   - Get your spam score (aim for 10/10)

---

## SendGrid Errors

### Error: "The from address does not match a verified Sender Identity"

**Solution:** Complete Step 3 (Verify Sender Identity)

### Error: "Unable to authenticate"

**Solution:**
- Verify API key is correct
- Ensure `MAIL_USERNAME=apikey` (exactly)
- Check for extra spaces in `.env`

### Error: "Daily sending limit reached"

**Solution:**
- Free plan: 100 emails/day
- Upgrade to paid plan for more volume
- Or wait for limit to reset (midnight UTC)

---

## Gmail Errors

### Error: "Username and Password not accepted"

**Solution:**
1. Ensure 2FA is enabled
2. Use App Password (not regular password)
3. Remove spaces from app password
4. Try generating new app password

### Error: "Less secure app access"

**Solution:**
- Google deprecated this
- Must use App Password with 2FA
- No other workaround

---

## DNS Propagation Issues

**If DNS records aren't working:**

1. **Wait longer** - Can take up to 48 hours (usually 10-30 minutes)

2. **Check DNS propagation:**
   - https://dnschecker.org/
   - Enter your domain
   - Select record type (TXT for SPF/DMARC)

3. **Clear DNS cache:**
   ```bash
   sudo systemd-resolve --flush-caches
   ```

4. **Verify with dig:**
   ```bash
   dig TXT jalsarovar.com +short
   dig TXT _dmarc.jalsarovar.com +short
   ```

---

# Email Service Checklist

## SendGrid Production Checklist

- [ ] SendGrid account created
- [ ] API key generated and saved
- [ ] Single sender verified OR domain authenticated
- [ ] Domain authentication completed (CNAME records added)
- [ ] `.env` file updated with SendGrid credentials
- [ ] SPF record added to DNS
- [ ] DMARC record added to DNS
- [ ] DKIM records added (via domain authentication)
- [ ] Application restarted
- [ ] Test email sent successfully
- [ ] Registration email verified working
- [ ] Password reset email verified working
- [ ] Emails not going to spam

## Gmail Production Checklist

- [ ] 2-Factor Authentication enabled on Gmail
- [ ] App Password generated
- [ ] `.env` file updated with Gmail credentials
- [ ] Application restarted
- [ ] Test email sent successfully
- [ ] Registration email working
- [ ] Password reset email working

**Note:** Gmail is NOT recommended for production. Use SendGrid for better deliverability.

---

# Next Steps

After email is configured:

1. Test all email templates:
   - Registration verification
   - Welcome email
   - Password reset
   - Role approval
   - Role rejection

2. Monitor email deliverability:
   - Check SendGrid Activity dashboard
   - Monitor bounce rates
   - Track open rates

3. Set up email alerting:
   - Configure alerts for high bounce rates
   - Monitor daily sending limits
   - Track spam complaints

4. Optimize email content:
   - Use branded templates
   - Include clear CTAs
   - Add unsubscribe links
   - Test across email clients

---

**Email Setup Complete!** ✅

Your Jal Sarovar application can now send emails for:
- User registration verification
- Password reset requests
- Role approval notifications
- Welcome messages

For support, check SendGrid documentation: https://docs.sendgrid.com/
