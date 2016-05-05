#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import atexit
from argparse import ArgumentParser
from collections import Counter
from pathlib import Path
import time
import asyncio
import signal

lock_file = Path.home() / '.rireki.pid'


class FileWatcher(object):
    _disabled = False

    def __init__(self, file, interval=0.2):
        self.interval = interval
        if isinstance(file, Path):
            self.file = file
        elif isinstance(file, str):
            self.file = Path(file)
        if self.file.is_file():
            self.mtime = self.file.stat().st_mtime
            self.remove_dupline()
        else:
            raise ValueError('File not exists: {}'.format(self.file))

    def is_modified(self):
        mtime = self.file.stat().st_mtime
        if mtime == self.mtime:
            return False
        else:
            self.mtime = mtime
            return True

    def remove_dupline(self):
        with self.file.open() as f:
            lines = f.readlines()
        counter = Counter(lines)
        if len(counter) == len(lines):
            return
        for k, v in ((k, v) for k, v in counter.items() if v > 1):
            for _ in range(v - 1):
                lines.remove(k)
        if not self.is_modified():
            with self.file.open('w') as f:
                f.write(''.join(lines))
            self.mtime = self.file.stat().st_mtime

    def watch(self):
        if self._disabled:
            return
        if self.is_modified():
            self.remove_dupline()
        asyncio.get_event_loop().call_later(self.interval, self.watch)

    def stop(self):
        self._disabled = True

    def start(self):
        self.watch()


@atexit.register
def cleanup():
    if lock_file.exists():
        lock_file.unlink()


def stop():
    if lock_file.exists():
        pid = int(lock_file.read_text().strip())
        os.kill(pid, signal.SIGINT)
        time.sleep(1)
        if lock_file.exists():
            lock_file.unlink()


def start():
    if lock_file.exists():
        stop()
    lock_file.write_text(str(os.getpid()))
    loop = asyncio.get_event_loop()
    f = os.environ.get('HIST_DIRS_FILE')
    if f:
        watcher = FileWatcher(f)
        watcher.start()
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            loop.close()


def main():
    parser = ArgumentParser()
    sub_persers = parser.add_subparsers()
    sub_persers.add_parser('start').set_defaults(func=start)
    sub_persers.add_parser('stop').set_defaults(func=stop)
    args = parser.parse_args()
    if 'func' not in args:
        print('Argument {strat,stop} required.')
        import sys
        sys.exit(1)
    else:
        args.func()


if __name__ == '__main__':
    main()
