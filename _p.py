import os
os.chdir(r'C:\Users\gjt\Desktop\ANMK8639-RK3568-H743')
with open(r'rk3568_app\modules\dashboard.html', 'rb') as f:
    data = f.read()

# 1. Show relay box always, not hidden
old_relay_hide = b'<div id=\"relay-url-box\" style=\"display:none;margin-bottom:8px\">'
new_relay_hide = b'<div id=\"relay-url-box\" style=\"margin-bottom:8px\">'
data = data.replace(old_relay_hide, new_relay_hide)
print('1. relay visibility:', old_relay_hide in data, '->', new_relay_hide in data)

# 2. Make relay video box same size as cam player
old_relay_vb = b'.relay-video-box{position:relative;width:100%;min-height:180px;background:#000;border-radius:4px;border:1px solid var(--border);overflow:hidden}'
new_relay_vb = b'.relay-video-box{position:relative;width:100%;min-height:240px;background:#000;border-radius:6px;border:1px solid var(--border);overflow:hidden}'
data = data.replace(old_relay_vb, new_relay_vb)
print('2. relay size:', old_relay_vb in data, '->', new_relay_vb in data)

# 3. Update relay CSS to match cam-player CSS closer  
# Add border-radius:6px to match
old_relay_rb = b'.relay-video-box img,.relay-video-box video'
new_relay_rb = b'.relay-video-box img,.relay-video-box video{position:absolute;top:0;left:0;width:100%;height:100%;object-fit:contain}\n.relay-video-box .relay-placeholder{position:absolute;top:0;left:0;right:0;bottom:0;display:flex;align-items:center;justify-content:center;color:var(--dim);font-size:13px}\n.relay-video-box .cam-loading-overlay{position:absolute;top:0;left:0;right:0;bottom:0;display:none;align-items:center;justify-content:center;background:rgba(0,0,0,0.65);z-index:10}\n.cam-preview img,.cam-preview video'
# Let me not do this - too fragile

# 4. Instead, simplify: remove separate relay CSS, make relay use cam-player class
# Actually let me just make the relay box more like left side

with open(r'rk3568_app\modules\dashboard.html', 'wb') as f:
    f.write(data)
print('Done, size:', len(data))
