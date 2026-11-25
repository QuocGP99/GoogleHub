"""HTML templates for the in-app authentication waiting screen."""


def get_auth_waiting_html(service_name):
    """Return Apple-inspired dark-themed waiting page HTML with hub:// action links."""
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Xác thực Google</title>
    <style>
        body {{
            background-color: #0D0D0F;
            color: #F5F5F7;
            font-family: "SF Pro Display", "SF Pro Text", -apple-system, BlinkMacSystemFont, "Segoe UI Variable", "Segoe UI", sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            -webkit-font-smoothing: antialiased;
        }}
        .card {{
            background: rgba(28, 28, 30, 0.88);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 18px;
            padding: 40px 42px;
            max-width: 440px;
            text-align: center;
            box-shadow: 0 24px 60px rgba(0, 0, 0, 0.65);
        }}
        .icon {{ font-size: 46px; margin-bottom: 14px; }}
        h2 {{
            margin: 0 0 10px 0;
            color: #F5F5F7;
            font-size: 20px;
            font-weight: 600;
            letter-spacing: -0.2px;
        }}
        p {{
            color: #98989D;
            font-size: 14px;
            line-height: 1.6;
            margin: 0 0 26px 0;
        }}
        .btn {{
            display: block;
            width: 100%;
            box-sizing: border-box;
            padding: 12px 18px;
            margin-bottom: 10px;
            border-radius: 11px;
            text-decoration: none;
            font-size: 14px;
            font-weight: 600;
            text-align: center;
            transition: background-color 0.18s ease, transform 0.12s ease;
        }}
        .btn-primary {{
            background-color: #0A84FF;
            color: #FFFFFF;
        }}
        .btn-primary:hover {{ background-color: #0070E0; }}
        .btn-secondary {{
            background-color: rgba(255, 255, 255, 0.06);
            color: #409CFF;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        .btn-secondary:hover {{ background-color: rgba(255, 255, 255, 0.12); }}
        .tip {{
            font-size: 12px;
            color: #6E6E73;
            margin-top: 18px;
            line-height: 1.45;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">🔑</div>
        <h2>Xác thực tài khoản Google</h2>
        <p>Google yêu cầu đăng nhập trên trình duyệt độc lập để bảo mật.<br>
        Cửa sổ Chrome/Edge đã được mở để bạn đăng nhập dịch vụ <b>{service_name}</b>.</p>
        <a href="hub://auth-complete" class="btn btn-primary">Tôi đã đăng nhập xong — Tiếp tục</a>
        <a href="hub://reopen-login" class="btn btn-secondary">Mở lại cửa sổ đăng nhập</a>
        <div class="tip">Ứng dụng sẽ tự động đồng bộ ngay khi bạn đăng nhập xong. Nếu chưa tự chuyển, hãy bấm nút xanh ở trên.</div>
    </div>
</body>
</html>"""
