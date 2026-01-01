# Deployment Guide for Desi Zaika Restaurant OS

## 🚀 Deploying to Render

### 1. Prerequisites
- Render account (sign up at https://render.com)
- GitHub repository with your code
- Supabase account (already configured)

### 2. Steps to Deploy

#### A. Prepare Your Repository
1. Make sure all your code is committed to GitHub
2. Ensure `.env` file is NOT in your repository (it's in .gitignore)
3. All environment variables will be set in Render dashboard

#### B. Create New Web Service on Render
1. Go to Render Dashboard → New → Web Service
2. Connect your GitHub repository
3. Configure:
   - **Name**: `desi-zaika-os` (or your preferred name)
   - **Region**: Choose closest to your customers (Mumbai/Singapore recommended)
   - **Branch**: `main` (or your default branch)
   - **Root Directory**: Leave empty (or `.` if needed)
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

#### C. Environment Variables in Render
Add these in Render Dashboard → Environment → Environment Variables:

```
DATABASE_URL=your_supabase_postgres_url
SECRET_KEY=your_secret_key_here (generate a strong random string)
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
```

#### D. Deploy
1. Click "Create Web Service"
2. Wait for deployment (usually 2-5 minutes)
3. Your app will be live at: `https://your-app-name.onrender.com`

---

## 📱 Generating QR Code for Customer Menu

### Option 1: Using Online QR Code Generator (Recommended)

1. **Get your menu URL**:
   - After deployment, your menu URL will be: `https://your-app-name.onrender.com/mobile`
   - Replace `your-app-name` with your actual Render app name

2. **Generate QR Code**:
   - Go to: https://www.qr-code-generator.com/ or https://qrcode.tec-it.com/
   - Enter URL: `https://your-app-name.onrender.com/mobile`
   - Choose QR code style (black & white recommended)
   - Download as PNG/SVG
   - Print and place on tables

### Option 2: Using Python (For Programmatic Generation)

```python
import qrcode

# Your menu URL
menu_url = "https://your-app-name.onrender.com/mobile"

# Generate QR code
qr = qrcode.QRCode(
    version=1,
    error_correction=qrcode.constants.ERROR_CORRECT_L,
    box_size=10,
    border=4,
)
qr.add_data(menu_url)
qr.make(fit=True)

# Create image
img = qrcode.make(menu_url)
img.save("menu_qr_code.png")
```

### Option 3: Using QR Code API

Visit: `https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=https://your-app-name.onrender.com/mobile`

Replace the URL and download the image.

---

## 🔪 Accessing Kitchen Display After Deployment

### Option 1: Direct URL (Easiest)
1. Kitchen URL: `https://your-app-name.onrender.com/kitchen`
2. Login with credentials:
   - Username: (your chef/kitchen staff username)
   - Password: (their password)
3. Bookmark this URL for quick access

### Option 2: Set Up a Dedicated Kitchen Tablet/Device
1. Use a tablet/iPad dedicated for kitchen
2. Open browser and go to: `https://your-app-name.onrender.com/kitchen`
3. Login once and keep the session active
4. Set browser to fullscreen mode (F11 on Windows, Cmd+Shift+F on Mac)
5. Optional: Use browser kiosk mode to prevent navigation

### Option 3: Create a Kitchen Shortcut
1. On kitchen device, create a desktop shortcut
2. Target URL: `https://your-app-name.onrender.com/kitchen`
3. Set browser to open in fullscreen automatically

### Recommended Kitchen Setup:
- **Device**: Tablet or large screen monitor (minimum 10 inches)
- **Mount**: Wall-mounted or counter stand
- **Orientation**: Landscape for better order visibility
- **Internet**: Stable WiFi connection
- **Browser**: Chrome/Firefox (auto-refresh enabled)

---

## 📍 Updated Restaurant Coordinates

Your restaurant coordinates have been updated to:
- **Latitude**: 28.654258822179788
- **Longitude**: 77.50614514922746

These are now active in the customer menu for location verification (50m radius).

---

## 🗑️ Resetting Order History

At the end of each day:
1. Go to Manager Dashboard
2. In "Recent History" section, click **"🗑️ Reset Today"** button
3. Confirm the action
4. This will delete all completed/cancelled orders from today
5. **Note**: This action cannot be undone - make sure you've reviewed today's data if needed

---

## 🔐 Security Notes for Production

1. **Change Default Passwords**: Update all default user passwords
2. **Use Strong SECRET_KEY**: Generate a strong random string for JWT tokens
3. **HTTPS**: Render automatically provides HTTPS
4. **Database Security**: Ensure Supabase has proper access controls
5. **Regular Backups**: Consider setting up database backups in Supabase

---

## 🐛 Troubleshooting

### Kitchen Display Not Loading
- Check if user is logged in
- Verify internet connection
- Clear browser cache and cookies
- Try incognito/private mode

### QR Code Not Working
- Verify the URL is correct
- Test the menu URL in a browser first
- Ensure QR code is printed clearly (minimum 2cm x 2cm)
- Use high contrast (black on white)

### Orders Not Showing in Kitchen
- Check if order status is "Pending"
- Verify kitchen staff has proper role (chef/waiter/manager)
- Check browser console for errors (F12)

---

## 📞 Support

For issues or questions:
1. Check Render logs: Dashboard → Your Service → Logs
2. Check browser console for frontend errors
3. Verify all environment variables are set correctly

Good luck with your deployment! 🎉

