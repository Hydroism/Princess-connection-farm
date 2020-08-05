import queue
import threading
import time
from io import BytesIO
from typing import Optional

import adbutils
import cv2
import matplotlib.pyplot as plt
import websocket

# from core.Automator import Automator
from pcr_config import debug, fast_screencut_timeout, fast_screencut_delay

lock = threading.Lock()


class ReceiveFromMinicap:
    def __init__(self, address):
        # 当前最后接收到的1帧数据
        self.receive_data = queue.Queue()
        # 接收标志位（每次接收1帧都会重置）
        self.receive_flag = 0
        # 关闭接收线程
        self.receive_close = 0
        # 模拟器地址
        self.address = address
        # 设置端口
        d = adbutils.adb.device(address)
        self.lport = d.forward_port(7912)
        # 这里设置websocket
        self.ws = websocket.WebSocketApp('ws://localhost:{}/minicap'.format(self.lport),
                                         # 这三个回调函数见下面
                                         on_message=self.on_message,
                                         on_close=self.on_close,
                                         on_error=self.on_error)
        self.receive_thread: Optional[threading.Thread] = None
        self.good_thread: Optional[threading.Thread] = None

    def start(self):
        if self.ws is None:
            raise Exception("请先建立与device的连接！")

        def run():
            while True:
                try:
                    self.ws.run_forever(ping_interval=30, ping_timeout=10)
                except Exception as e:
                    if debug:
                        print("run minicap", type(e), e)

        if self.receive_thread is None:
            self.receive_thread = threading.Thread(target=run, name="minicap_thread", daemon=True)
            self.receive_thread.start()

    # 接收信息回调函数，此处message为接收的信息
    def on_message(self, message):
        if message is not None:
            if self.receive_flag is 1:
                # 如果不是bytes，那就是图像
                if isinstance(message, (bytes, bytearray)) and len(message) > 100:
                    self.receive_data.put(message)
                    self.receive_flag = 0
                else:
                    if debug:
                        print(message)

    # 错误回调函数
    def on_error(self, error):
        print(error)

    # 关闭ws的回调函数
    def on_close(self):
        if debug:
            print("### closed ###")

    # 开始接收1帧画面
    def receive_img(self):
        retry = 0
        max_retry = 3
        while retry <= max_retry:
            self.receive_flag = 1
            try:
                data = self.receive_data.get(timeout=fast_screencut_timeout)
                if debug:
                    print("data len:", len(data))
                data = BytesIO(data)
                data = plt.imread(data, "jpg")
                # 转rgb
                data = cv2.cvtColor(data, cv2.COLOR_BGR2RGB)
                time.sleep(fast_screencut_delay)
                return data
            except queue.Empty:
                # 读取超时
                if debug:
                    print("读取超时")
                retry += 1
                continue
            except Exception as e:
                if debug:
                    print("receive_img", type(e), e)
                retry += 1
                continue
        if debug:
            print("快速截图失败！")
            return None


# if __name__ == '__main__':
#     a = Automator("emulator-5554")
#     # 这个Automator只是需要他的端口而已
#     rfm = ReceiveFromMinicap(a.lport)
#
#     # 启动线程
#     socket_thread = rfm.ReceiveThread(rfm.ws)
#     socket_thread.start()
#
#     time.sleep(5)
#
#     for i in range(50):
#         with open("test/testMC.jpg", "wb") as f:
#             f.write(rfm.receive_data)
#         time.sleep(1)
#
#     rfm.receive_close = 1
#     socket_thread.join()
