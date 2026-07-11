"""Echo 智慧管理中心 - Flask 应用入口"""
import logging
from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_compress import Compress

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

logger.info("=" * 50)
logger.info("Starting Echo...")
logger.info(f"Working dir: {__import__('os').getcwd()}")
logger.info("=" * 50)


def create_app():
    """创建 Flask 应用"""
    app = Flask(__name__, static_folder='static')
    CORS(app, origins=['http://localhost:5001', 'http://127.0.0.1:5001', 'http://localhost:5173', 'http://127.0.0.1:5173'])
    Compress(app)

    # SECRET_KEY 持久化
    import os
    _SECRET_KEY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.secret_key')
    if os.environ.get('SECRET_KEY'):
        app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
    elif os.path.exists(_SECRET_KEY_FILE):
        with open(_SECRET_KEY_FILE, 'r') as f:
            app.config['SECRET_KEY'] = f.read().strip()
    else:
        app.config['SECRET_KEY'] = os.urandom(32).hex()
        with open(_SECRET_KEY_FILE, 'w') as f:
            f.write(app.config['SECRET_KEY'])
        os.chmod(_SECRET_KEY_FILE, 0o600)
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB 上传大小限制

    # 错误处理器
    from werkzeug.exceptions import BadRequest
    from flask import jsonify

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({'error': '请求参数错误'}), 400

    @app.errorhandler(BadRequest)
    def handle_bad_request(e):
        return jsonify({'error': '请求体格式错误或参数无效'}), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': '资源不存在'}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({'error': '请求方法不允许'}), 405

    @app.errorhandler(413)
    def request_entity_too_large(e):
        return jsonify({'error': '请求体超过大小限制(最大16MB)'}), 413

    @app.errorhandler(429)
    def too_many_requests(e):
        return jsonify({'error': '请求过于频繁，请稍后再试'}), 429

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({'error': '服务器内部错误'}), 500

    # 中间件
    import time
    from flask import g, request

    @app.after_request
    def add_cache_headers(response):
        if request.path.startswith('/static/') and not request.path.startswith('/static/uploads/'):
            response.headers['Cache-Control'] = 'public, max-age=86400'
        elif request.path.startswith('/api/stats') or request.path.startswith('/api/tags'):
            response.headers['Cache-Control'] = 'private, max-age=60'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        return response

    @app.before_request
    def before_request_timing():
        g.start_time = time.time()

    @app.after_request
    def after_request_timing(response):
        if hasattr(g, 'start_time'):
            elapsed = time.time() - g.start_time
            response.headers['X-Response-Time'] = f'{elapsed*1000:.1f}ms'
            if elapsed > 1.0:
                logger.warning(f'慢请求: {request.method} {request.path} 耗时 {elapsed:.2f}s')
        return response

    # 数据库连接管理
    from db import get_db, close_db, init_db
    app.teardown_appcontext(close_db)

    # 静态文件路由
    @app.route('/')
    def index():
        return send_from_directory('static', 'index.html')

    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(app.static_folder, 'favicon.ico', mimetype='image/x-icon')

    @app.route('/api/health')
    def health():
        """健康检查端点"""
        try:
            get_db().execute('SELECT 1')
            return jsonify({'status': 'ok', 'db': 'connected'}), 200
        except Exception as e:
            logger.error(f'数据库连接失败: {e}')
            return jsonify({'status': 'error', 'db': 'unavailable'}), 503

    # 注册蓝图
    from routes import auth_bp, articles_bp, kiwi_sales_bp, overtime_bp, expenses_bp
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(articles_bp, url_prefix='/api')
    app.register_blueprint(kiwi_sales_bp, url_prefix='/api')
    app.register_blueprint(overtime_bp, url_prefix='/api')
    app.register_blueprint(expenses_bp, url_prefix='/api')

    return app


if __name__ == '__main__':
    from db import init_db
    init_db()
    app = create_app()
    logger.info("=" * 60)
    logger.info("  Echo started!")
    logger.info("  API: http://localhost:5001/api")
    logger.info("  Web: http://localhost:5001")
    logger.info("=" * 60)
    app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)
