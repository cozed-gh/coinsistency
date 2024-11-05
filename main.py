import logging
import multiprocessing as mp
import py.background_process as bp
from routes import app

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

if __name__ in ['__main__', 'main']:
    mp.Process(name="Backend Daemon", target=bp.init, daemon=True).start()
    app.run()