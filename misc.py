class RWLock():
    def __init__(self):
        import threading
        self._writer_lock=threading.RLock()
        self._reader_lock=threading.RLock()
        self._count_lock=threading.RLock()
        self._count=0

    def writerAcquire(self):
        self._reader_lock.acquire()
        self._writer_lock.acquire()

    def writerRelease(self):
        self._writer_lock.release()
        self._reader_lock.release()

    def readerAcquire(self):
        self._reader_lock.acquire()
        self._count_lock.acquire()
        if self._count==0:
            self._writer_lock.acquire()
        self._count+=1
        self._count_lock.release()
        self._reader_lock.release()

    def readerRelease(self):
        self._count_lock.acquire()
        self._count-=1
        if self._count==0:
            self._writer_lock.release()
        self._count_lock.release()

def printLog(data):
	print(data, file=logfile)
	logfile.flush()

def crypto(s):
	import hashlib
	return hashlib.md5(s.encode()).hexdigest()

import sys
logfile=sys.stdout

