import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import threading
from bs4 import BeautifulSoup
import chardet

class FolderToTextApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CHM文件夹 -> NotebookLM 转换器 (修复版)")
        # 1. 修改：窗口改大一点 (600宽 x 500高)
        self.root.geometry("600x500")
        # 2. 修改：允许你用鼠标拉伸窗口大小 (如果还看不见，就拉大窗口)
        self.root.resizable(True, True)

        # 变量
        self.folder_path = tk.StringVar()
        self.status_var = tk.StringVar()
        self.status_var.set("准备就绪 - 等待选择文件夹")
        
        # 布局容器
        main_frame = tk.Frame(root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- 顶部说明区 ---
        tk.Label(main_frame, text="第一步：选择解压后的文件夹", font=("微软雅黑", 12, "bold")).pack(anchor="w", pady=(0, 5))
        tk.Label(main_frame, text="请先用 7-Zip/WinRAR 把 CHM 解压出来，然后选那个文件夹。", font=("微软雅黑", 9), fg="#666").pack(anchor="w")
        
        # --- 文件选择区 ---
        file_frame = tk.Frame(main_frame, pady=10)
        file_frame.pack(fill=tk.X)
        
        # 输入框
        entry = tk.Entry(file_frame, textvariable=self.folder_path, font=("微软雅黑", 10))
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        # 浏览按钮
        btn_browse = tk.Button(file_frame, text="📁 浏览文件夹...", command=self.select_folder, height=1)
        btn_browse.pack(side=tk.LEFT)

        tk.Label(main_frame, text="------------------------------------------------", fg="#ccc").pack(pady=10)

        # --- 说明区 ---
        info_text = (
            "使用说明：\n"
            "1. 只要你选对了文件夹，软件会自动扫描里面的网页。\n"
            "2. 自动合并文字，并按 20万字/个 切割。\n"
            "3. 转换后的文件会生成在文件夹旁边。"
        )
        tk.Label(main_frame, text=info_text, justify=tk.LEFT, fg="#444", font=("微软雅黑", 10), bg="#f0f0f0", padx=10, pady=10).pack(fill=tk.X, pady=(0, 20))

        # --- 底部操作区 (这里使用了 pack(side=BOTTOM) 确保按钮永远在最底下) ---
        bottom_frame = tk.Frame(main_frame)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)

        # 状态标签
        tk.Label(bottom_frame, textvariable=self.status_var, fg="blue", font=("微软雅黑", 9)).pack(pady=5)

        # 进度条
        self.progress = ttk.Progressbar(bottom_frame, orient=tk.HORIZONTAL, length=100, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=5)

        # 🟢 巨大的开始按钮
        self.btn_start = tk.Button(bottom_frame, text="🚀 开始转换", command=self.start_thread, 
                                   bg="#4CAF50", fg="white", font=("微软雅黑", 14, "bold"), height=2)
        self.btn_start.pack(fill=tk.X, pady=10)

    def select_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.folder_path.set(folder_selected)

    def start_thread(self):
        if not self.folder_path.get():
            messagebox.showwarning("提示", "请先点击“浏览文件夹”按钮！")
            return
        
        self.btn_start.config(state=tk.DISABLED, text="正在处理中...")
        self.progress.start(10)
        threading.Thread(target=self.run_process, daemon=True).start()

    def run_process(self):
        try:
            source_dir = self.folder_path.get()
            # 输出目录设为：原文件夹名字_转换结果
            folder_name = os.path.basename(os.path.normpath(source_dir))
            output_dir = os.path.join(os.path.dirname(os.path.normpath(source_dir)), f"{folder_name}_转文本结果")
            
            self.status_var.set("正在扫描网页文件...")
            
            # 1. 扫描
            html_files = []
            for root, _, files in os.walk(source_dir):
                for file in files:
                    if file.lower().endswith(('.htm', '.html')):
                        html_files.append(os.path.join(root, file))
            
            if not html_files:
                self.progress.stop()
                self.btn_start.config(state=tk.NORMAL, text="🚀 开始转换")
                self.status_var.set("错误：没找到网页文件")
                messagebox.showerror("错误", "在这个文件夹里没找到网页文件(.html)。\n请确认你选的是解压后的文件夹。")
                return

            html_files.sort()
            self.status_var.set(f"找到 {len(html_files)} 个网页，开始提取...")

            # 2. 提取与合并
            full_text_chunks = []
            current_chunk = []
            current_size = 0
            max_chars = 200000 
            
            total_files = len(html_files)

            for i, html_path in enumerate(html_files):
                if i % 20 == 0:
                    self.status_var.set(f"正在处理进度: {int((i/total_files)*100)}% ...")

                text = self.extract_text(html_path)
                if not text: continue

                header = f"\n\n=== 来源章节: {os.path.basename(html_path)} ===\n\n"
                content = header + text
                
                current_chunk.append(content)
                current_size += len(content)

                if current_size >= max_chars:
                    full_text_chunks.append("".join(current_chunk))
                    current_chunk = []
                    current_size = 0
            
            if current_chunk:
                full_text_chunks.append("".join(current_chunk))

            # 3. 保存
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            self.status_var.set("正在保存文件...")
            for idx, chunk in enumerate(full_text_chunks):
                out_name = f"投喂包_{idx+1:02d}.txt"
                with open(os.path.join(output_dir, out_name), 'w', encoding='utf-8') as f:
                    f.write(chunk)

            self.status_var.set("完成！")
            messagebox.showinfo("成功", f"转换完成！\n共生成 {len(full_text_chunks)} 个txt文件。\n\n文件夹已自动打开。")
            os.startfile(output_dir)

        except Exception as e:
            messagebox.showerror("错误", f"发生错误：\n{str(e)}")
            self.status_var.set("发生错误")
        
        finally:
            self.progress.stop()
            self.btn_start.config(state=tk.NORMAL, text="🚀 开始转换")

    def extract_text(self, path):
        try:
            with open(path, 'rb') as f:
                raw = f.read(10000)
            enc = chardet.detect(raw)['encoding'] or 'utf-8'
            
            with open(path, 'r', encoding=enc, errors='ignore') as f:
                soup = BeautifulSoup(f, 'html.parser')
                return soup.get_text(separator='\n', strip=True)
        except:
            return ""

if __name__ == "__main__":
    root = tk.Tk()
    app = FolderToTextApp(root)
    root.mainloop()