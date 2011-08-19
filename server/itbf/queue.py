from lockfile import FileLock
import pickle
import os

QUEUE_FILE = os.path.dirname(os.path.realpath(__file__)) + '/../data/buildfaster-queue.pkl'

# Internal utility methods

def _get_queue():
    try:
        return pickle.load(open(QUEUE_FILE, 'r'))
    except:
        print "No queue, creating."
        return []

def _save_queue(queue):
    pickle.dump(queue, open(QUEUE_FILE, 'wb'))


# Accessor methods

def append_job(tree, revision, submitter, return_email):
    lock = FileLock(QUEUE_FILE)
    with lock:
        queue = _get_queue()
        queue.append({'tree': tree, 'revision': revision,
                      'submitter': submitter,
                      'return_email': return_email })
        _save_queue(queue)

def pop_job():
    lock = FileLock(QUEUE_FILE)
    with lock:
        queue = _get_queue()
        next_job = None
        if len(queue) > 0:
            next_job = queue.pop()
            _save_queue(queue)
        return next_job

def get_copy():
    return _get_queue()

def clear():
    lock = FileLock(QUEUE_FILE)
    with lock:
        _save_queue([])
