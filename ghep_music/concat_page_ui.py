import tkinter as tk
from tkinter import ttk


class ConcatPageUIMixin:
    def _build_ui(self):
        self.frm_top = ttk.LabelFrame(self, text="ƒsT‹,? Configuration", padding=(10, 10))
        # Channel selection + Concat mode cA1ng hAÿng
        channel_frame = ttk.Frame(self.frm_top)
        channel_frame.grid(row=0, column=0, columnspan=4, sticky="we", pady=5)
        for c in (1, 2, 4, 6, 7):
            channel_frame.grid_columnconfigure(c, weight=1)

        ttk.Label(channel_frame, text="Profile:", font=("Trebuchet MS", 10, "bold")).grid(row=0, column=0, sticky="e", padx=5)
        self.combo_channel = ttk.Combobox(
            channel_frame, textvariable=self.selected_channel, values=self._list_channels(),
            width=25, state="readonly", font=("Trebuchet MS", 10)
        )
        self.combo_channel.grid(row=0, column=1, sticky="ew", padx=5)
        self.combo_channel.bind("<<ComboboxSelected>>", self._on_channel_change)
        self._add_right_click_menu(self.combo_channel,[("dY-` Delete Channel", self._clear_channel_selection),])

        # --- Input Ž` ¯Ÿ nh §-p tA¦n channel m ¯>i ---
        self.entry_new_channel = ttk.Entry(channel_frame, width=20, font=("Trebuchet MS", 10))
        self.entry_new_channel.grid(row=0, column=2, sticky="ew", padx=5)

        def on_focus_in(e):
            if self.entry_new_channel.get() == "Enter channel name...":
                self.entry_new_channel.delete(0, "end")

        def on_focus_out(e):
            if not self.entry_new_channel.get().strip():
                self.entry_new_channel.insert(0, "Enter channel name...")

        self.entry_new_channel.insert(0, "Enter channel name...")
        self.entry_new_channel.bind("<FocusIn>", on_focus_in)
        self.entry_new_channel.bind("<FocusOut>", on_focus_out)
        self.entry_new_channel.bind("<Return>", self._create_channel_from_entry)

        # --- Concat mode ngay c §­nh ---
        ttk.Label(channel_frame, text="Concat mode:", font=("Trebuchet MS", 10, "bold")).grid(row=0, column=3, sticky="e", padx=(15,5))
        self.combo_mode = ttk.Combobox(
            channel_frame, textvariable=self.concat_mode, state="readonly", width=60,justify='center', font=("Trebuchet MS", 10),
            values=[
                "Concat with music background",
                "Concat with first video",
                "Concat with outro music",
                "Normal concat (no music)",
                "Concat and Reverse",
                "Concat with time limit",
                "Loop",
                'Tuan Seo Custom'
            ]
        )
        self.combo_mode.grid(row=0, column=4, sticky="ew", padx=5)
        self.combo_mode.current(0)
        self.combo_mode.bind("<<ComboboxSelected>>", lambda e: (self.save_channel_config(force=True), self._update_mode_visibility(), self.reload_groups()))

        self.btn_advanced = ttk.Button(
            channel_frame, text="Advanced", style="Advanced.TButton",
            command=self._toggle_advanced
        )
        self.btn_advanced.grid(row=0, column=8, sticky="w", padx=8)

        # Parameters frame
        param_frame = ttk.Frame(self.frm_top)
        param_frame.grid(row=1, column=0, columnspan=4, sticky="we", pady=5)
        param_frame.grid_columnconfigure(5, weight=1)   
        param_frame.grid_columnconfigure(1, weight=0)  

        self.lbl_group_size = ttk.Label(param_frame, text="Videos per Group:", font=("Trebuchet MS", 10, "bold"))
        self.lbl_group_size.grid(row=0, column=0, sticky="e", padx=5)
        self.combo_group_size = ttk.Combobox(
            param_frame, textvariable=self.group_size_var, values=list(range(1, 101)),
            width=6, state="readonly", font=("Trebuchet MS", 10)
        )
        self.combo_group_size.grid(row=0, column=1, sticky="w", padx=5)
        self.combo_group_size.bind("<<ComboboxSelected>>", self._on_group_size_change)

        self.lbl_limit_videos = ttk.Label(param_frame, text="Total Videos to Export:", font=("Trebuchet MS", 10, "bold"))
        self.lbl_limit_videos.grid(row=0, column=2, sticky="e", padx=(10, 4))
        
        limit_display = ["All"] + [str(i) for i in range(1, 101)]
        self.limit_videos_display = tk.StringVar(value="All")  # StringVar Ž` ¯Ÿ hi ¯Ÿn th ¯<
        self.combo_limit_videos = ttk.Combobox(
            param_frame, width=8, state="readonly",
            textvariable=self.limit_videos_display, values=limit_display
        )
        self.combo_limit_videos.grid(row=0, column=3, sticky="w", padx=(0, 5))
        self.combo_limit_videos.set("All")  # hi ¯Ÿn th ¯< "All"

        def on_limit_change(event=None):
            val = self.combo_limit_videos.get()
            self.limit_videos_var.set(0 if val == "All" else int(val))
            self.reload_groups()
            self.save_channel_config(force=True)
        self.combo_limit_videos.bind("<<ComboboxSelected>>", on_limit_change)
        self.combo_limit_videos.grid(row=0, column=3, sticky="ew", padx=5)

        # --- Time limit (minutes) - ch ¯% hi ¯Øn  ¯Y "Concat with time limit"
        self.lbl_time_limit = ttk.Label(param_frame, text="Time limit (min):", font=("Trebuchet MS", 10, "bold"))
        self.lbl_time_limit.grid(row=0, column=4, sticky="e", padx=(15,5))

        self.combo_time_limit = ttk.Combobox(
            param_frame, textvariable=self.time_limit_min_var, state="normal",
            width=6, values=list(range(0, 1000))
        )
        self.combo_time_limit.grid(row=0, column=5, sticky="w", padx=5)
        self.lbl_time_limit.grid_configure(column=7)
        self.combo_time_limit.grid_configure(column=8)

        #---- Second selection ------
        self.combo_time_limit_sec = ttk.Combobox(
            param_frame, textvariable=self.time_limit_sec_var, state='normal',
            width=6, values=list(range(0,60))
        )
        self.combo_time_limit_sec.grid(row=0, column=10, sticky='w', padx=5)

        self.btn_first_videos = ttk.Button(
            param_frame,
            text="First video",
            style="Secondary.TButton",
            command=self._open_first_videos_table,
        )
        self.btn_first_videos.grid(row=2, column=1, sticky="w", padx=5)

        self.btn_first_videos.grid_remove()

        def select_all_text(event):
            event.widget.selection_range(0, 'end')
            return 'break'  # trA­nh behavior m §úc Ž` ¯<nh

        self.combo_time_limit.bind("<FocusIn>", select_all_text)
        self.combo_time_limit_sec.bind("<FocusIn>", select_all_text)
        self.combo_time_limit.bind("<<ComboboxSelected>>", lambda e: self.save_channel_config())
        self.combo_time_limit_sec.bind("<<ComboboxSelected>>", lambda e: self.save_channel_config())

        def _commit_time_limit(event=None):
            if getattr(self, "_loading", False):
                return
            m = (self.time_limit_min_var.get() or "").strip()
            s = (self.time_limit_sec_var.get() or "").strip()

            m = "0" if not m.isdigit() else m
            s = "0" if not s.isdigit() else s

            m_i = min(int(m), 999)
            s_i = min(int(s), 59)

            self.time_limit_min_var.set(str(m_i))
            self.time_limit_sec_var.set(str(s_i))
            self.save_channel_config(force=True)
            self.reload_groups() 
        
        self.combo_time_limit.bind("<FocusOut>", _commit_time_limit)
        self.combo_time_limit_sec.bind("<FocusOut>", _commit_time_limit)
        self.combo_time_limit.bind("<Return>", _commit_time_limit)
        self.combo_time_limit_sec.bind("<Return>", _commit_time_limit)
        self.time_limit_min_var.trace_add("write", self._on_time_limit_var_changed)
        self.time_limit_sec_var.trace_add("write", self._on_time_limit_var_changed)

        self.slider_volume = ttk.Scale(param_frame, from_=0.0, to=1.0, orient="horizontal", variable=self.bgm_volume_var, length=120)
        self.slider_volume.grid(row=0, column=5, sticky="ew", padx=5)
        self.lbl_volume = ttk.Label(param_frame, text=f"{self.bgm_volume_var.get() * 100:.0f}%", width=5)
        self.lbl_volume.grid(row=0, column=6, sticky="ew", padx=5)

        # --- Main Video Volume Slider ---
        self.lbl_main_video_vol = ttk.Label(param_frame, text="Video Volume:", font=("Trebuchet MS", 10, "bold"))
        self.lbl_main_video_vol.grid(row=2, column=4, sticky="e", padx=5)

        self.slider_main_video_vol = ttk.Scale(
            param_frame, from_=0.0, to=2.0, orient="horizontal", variable=self.main_video_volume_var, length=120
        )
        self.slider_main_video_vol.grid(row=2, column=5, sticky="ew", padx=5)

        self.lbl_main_video_vol_value = ttk.Label(param_frame, text=f"{self.main_video_volume_var.get() * 100:.0f}%", width=5)
        self.lbl_main_video_vol_value.grid(row=2, column=6, sticky="ew", padx=5)

        # --- Video Volume Slider ---
        self.lbl_video_vol = ttk.Label(param_frame, text="Outro Volume:", font=("Trebuchet MS", 10, "bold"))
        self.lbl_video_vol.grid(row=1, column=4, sticky="e", padx=5)

        self.slider_video_vol = ttk.Scale(
            param_frame, from_=0.0, to=1.0, orient="horizontal", variable=self.video_volume_var, length=120
        )
        self.slider_video_vol.grid(row=1, column=5, sticky="ew", padx=5)

        self.lbl_video_vol_value = ttk.Label(param_frame, text=f"{self.video_volume_var.get() * 100:.0f}%", width=5)
        self.lbl_video_vol_value.grid(row=1, column=6, sticky="w", padx=5)

        # --- Outro Length (seconds) ---
        self.lbl_outro_dur = ttk.Label(param_frame, text="Outro length (s):", font=("Trebuchet MS", 10, "bold"))
        self.lbl_outro_dur.grid(row=1, column=7, sticky="e", padx=5)

        self.cbo_outro_dur = ttk.Combobox(
            param_frame, textvariable=self.outro_duration_var, state="readonly", width=6,
            values= [5, 10, 12, 15, 20, 30, 45, 60, 90, 120]
        )
        self.cbo_outro_dur.grid(row=1, column=8, sticky="w", padx=5)
        # l’øu config khi Ž` ¯i l ¯ña ch ¯?n
        self.cbo_outro_dur.bind("<<ComboboxSelected>>", lambda e: self.save_channel_config())

        self.video_volume_var.trace_add("write", self._update_video_volume_label)
        self.bgm_volume_var.trace_add("write", self._update_volume_label)

        self.lbl_bgm_text = ttk.Label(param_frame, text="BGM Volume:", font=("Trebuchet MS", 10, "bold"))
        self.lbl_bgm_text.grid(row=0, column=4, sticky="e", padx=5)

        # --- Outro Mode ---
        self.lbl_outro_mode = ttk.Label(channel_frame, text="Outro mode:", font=("Trebuchet MS", 10, "bold"))
        self.lbl_outro_mode.grid(row=0, column=5, sticky="e", padx=(10, 5))
        self.combo_outro_mode = ttk.Combobox(
            channel_frame,
            textvariable=self.outro_mode_var,
            state="readonly",
            width=15,
            values=["By group count", "By time limit"]
        )
        self.combo_outro_mode.grid(row=0, column=6, sticky="ew", padx=5)
        self.combo_outro_mode.bind("<<ComboboxSelected>>", lambda e: (self.save_channel_config(), self._update_mode_visibility()))

        # self.btn_reload = ttk.Button(param_frame, text="ƒ+¯ Reload", style="Accent.TButton", command=self.reload_groups)
        # self.btn_reload.grid(row=0, column=7, sticky="w", padx=5)

        # --- Video Settings Frame ---
        self.video_frame = ttk.LabelFrame(self.frm_top, text="dYZª Video Settings", padding=(10,5))
        self.video_frame.grid(row=2, column=0, columnspan=4, sticky="we", pady=5)
        for c in (1,3,5,6):
            self.video_frame.grid_columnconfigure(c, weight=1)

        # Preset lists
        cq_values = [10, 12, 15, 17, 18, 20, 21, 22, 23, 24, 25, 28, 30, 32, 35, 40]
        v_bitrate_values = ["4M", "6M", "8M", "10M", "12M", "15M", "20M", "25M", "30M","35M","45M","55M","68M","85M","100M","120M"]
        a_bitrate_values = ["96k", "128k", "160k", "192k", "256k", "320k"]

        # HAÿng 1
        ttk.Label(self.video_frame, text="Resolution:", font=("Trebuchet MS", 10, "bold")).grid(row=0, column=0, sticky="e", padx=5)
        ttk.Combobox(
            self.video_frame, textvariable=self.resolution_var, width=10, state="readonly",
            values=[
                "1080x1920","1920x1080","720x1280","1280x720",
                "1440x2560","2560x1440",     # 2K
                "2160x3840","3840x2160"      # 4K
            ]
        ).grid(row=0, column=1, sticky="w")

        ttk.Label(self.video_frame, text="FPS:", font=("Trebuchet MS", 10, "bold")).grid(row=0, column=2, sticky="e", padx=5)
        ttk.Combobox(self.video_frame, textvariable=self.fps_var, width=5, state="readonly",
                    values=[24, 30, 60, 120]).grid(row=0, column=3, sticky="w")

        ttk.Label(self.video_frame, text="CQ / CRF:", font=("Trebuchet MS", 10, "bold")).grid(row=0, column=4, sticky="e", padx=5)
        self.cbo_cq = ttk.Combobox(self.video_frame, textvariable=self.cq_var, width=5, state="readonly", values=cq_values)
        self.cbo_cq.grid(row=0, column=5, sticky="w")

        self.btn_nvenc = ttk.Button(
            self.video_frame,
            text="NVENC ON" if self.use_nvenc_var.get() else "NVENC OFF",
            style="Secondary.TButton",
            command=self._toggle_nvenc
        )
        self.btn_nvenc.grid(row=0, column=6, padx=(10,0), sticky="w")
        self.use_nvenc_var.trace_add("write", self._update_nvenc_button)

        # HAÿng 2
        ttk.Label(self.video_frame, text="Video Bitrate:", font=("Trebuchet MS", 10, "bold")).grid(row=1, column=0, sticky="e", padx=5)
        self.cbo_vbit = ttk.Combobox(self.video_frame, textvariable=self.v_bitrate_var, width=8, state="readonly", values=v_bitrate_values)
        self.cbo_vbit.grid(row=1, column=1, sticky="w")

        ttk.Label(self.video_frame, text="Audio Bitrate:", font=("Trebuchet MS", 10, "bold")).grid(row=1, column=2, sticky="e", padx=5)
        self.cbo_abit = ttk.Combobox(self.video_frame, textvariable=self.a_bitrate_var, width=8, state="readonly", values=a_bitrate_values)
        self.cbo_abit.grid(row=1, column=3, sticky="w")

        ttk.Label(self.video_frame, text="Preset:", font=("Trebuchet MS", 10, "bold")).grid(row=1, column=4, sticky="e", padx=5)
        ttk.Combobox(self.video_frame, textvariable=self.nvenc_preset_var, width=6, state="readonly",
                    values=["p1","p2","p3","p4","p5","p6","p7","medium"]).grid(row=1, column=5, sticky="w")

        #  §"N m §úc Ž` ¯<nh (gi ¯_ logic Advanced)
        cut_frame = ttk.Frame(self.video_frame)
        cut_frame.grid(row=2, column=0, columnspan=7, sticky="w", pady=(6, 0))
        ttk.Label(cut_frame, text="Cut:", font=("Trebuchet MS", 10, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(
            cut_frame,
            text="Apply first video",
            variable=self.cut_scope_var,
            value="first",
            command=self._on_cut_scope_change,
        ).grid(row=0, column=1, sticky="w", padx=(8, 12))
        ttk.Radiobutton(
            cut_frame,
            text="Apply all videos",
            variable=self.cut_scope_var,
            value="all",
            command=self._on_cut_scope_change,
        ).grid(row=0, column=2, sticky="w", padx=(8, 12))

        ttk.Label(cut_frame, text="First frame:").grid(row=1, column=1, sticky="w", padx=(8, 4), pady=(2, 0))
        ttk.Entry(cut_frame, textvariable=self.cut_frame_first_var, width=6).grid(row=1, column=2, sticky="w", pady=(2, 0))
        ttk.Label(cut_frame, text="Last frame:").grid(row=2, column=1, sticky="w", padx=(8, 4), pady=(2, 0))
        ttk.Entry(cut_frame, textvariable=self.cut_frame_last_var, width=6).grid(row=2, column=2, sticky="w", pady=(2, 0))

        self.video_frame.grid_remove()

        # Ž? §œm b §œo giA­ tr ¯< hi ¯Øn t §­i Ž`’ø ¯œc ch ¯?n ngay c §œ khi khA'ng n §ñm trong preset
        if self.cq_var.get() not in cq_values:
            self.cbo_cq["values"] = [self.cq_var.get()] + cq_values
        if self.v_bitrate_var.get() and self.v_bitrate_var.get() not in v_bitrate_values:
            self.cbo_vbit["values"] = [self.v_bitrate_var.get()] + v_bitrate_values
        if self.a_bitrate_var.get() and self.a_bitrate_var.get() not in a_bitrate_values:
            self.cbo_abit["values"] = [self.a_bitrate_var.get()] + a_bitrate_values

        # Folder selection
        folder_frame = ttk.LabelFrame(self.frm_top, text="Folders", padding=(10, 5))
        folder_frame.grid(row=3, column=0, columnspan=4, sticky="we", pady=5)
        folder_frame.grid_columnconfigure(1, weight=1)
        folder_frame.grid_columnconfigure(2, weight=1)
        self._add_folder_row("Source Folder:", self.input_folder, 0, folder_frame, reload=True)
        self._add_folder_row("Save Folder:", self.save_folder, 1, folder_frame)
        self.music_widgets = self._add_folder_row("Music Folder:", self.bgm_folder, 2, folder_frame, bgm=True)
        # Action buttons and progress
        action_frame = ttk.Frame(self.frm_top)
        action_frame.grid(row=4, column=0, columnspan=4, sticky="we", pady=10)
        action_frame.grid_columnconfigure(0, weight=0)
        action_frame.grid_columnconfigure(1, weight=0)
        action_frame.grid_columnconfigure(2, weight=0)
        action_frame.grid_columnconfigure(3, weight=0)
        action_frame.grid_columnconfigure(4, weight=1)
        action_frame.grid_columnconfigure(5, weight=0)

        self.btn_concat = ttk.Button(action_frame, text="Start", style="Accent.TButton", command=self.start_concat)
        self.btn_concat.grid(row=0, column=0, padx=5, pady=(0, 6), sticky="w")
        self.btn_stop = ttk.Button(action_frame, text="Stop", style="Stop.TButton", command=self.stop_concat, state=tk.DISABLED)
        self.btn_stop.grid(row=0, column=1, padx=5, pady=(0, 6), sticky="w")
        self.btn_open = ttk.Button(action_frame, text="Open Folder", style="Secondary.TButton", command=self.open_output_folder)
        self.btn_open.grid(row=0, column=2, padx=5, pady=(0, 6), sticky="w")
        self.btn_clear = ttk.Button(action_frame, text="Clear Log", style="Secondary.TButton", command=self.clear_log)
        self.btn_clear.grid(row=0, column=3, padx=5, pady=(0, 6), sticky="w")

        self.progress = ttk.Progressbar(action_frame, orient="horizontal", mode="determinate")
        self.progress.grid(row=1, column=0, columnspan=5, padx=5, sticky="ew")
        self.lbl_status = ttk.Label(action_frame, textvariable=self.status_var, font=("Trebuchet MS", 10, "italic"))
        self.lbl_status.grid(row=1, column=5, padx=(6, 0), sticky="w")

        self.progress_infor_var = tk.StringVar(value='')
        self.lbl_progress_info = ttk.Label(
            action_frame, textvariable=self.progress_infor_var, font=("Trebuchet MS", 9, "italic")
        )
        self.lbl_progress_info.grid(row=2, column=0, columnspan=5, padx=5, pady=(2, 0), sticky='w')

        # Job progress
        self.job_info_var = tk.StringVar(value='')
        self.progress_job = ttk.Progressbar(action_frame, orient="horizontal", mode='determinate', maximum=100, value=0)
        self.progress_job.grid(row=3, column=0, columnspan=5, padx=5, sticky='ew')

        self.lbl_job_info = ttk.Label(action_frame, textvariable=self.job_info_var, font=("Trebuchet MS", 9, "italic"))
        self.lbl_job_info.grid(row=4, column=0, columnspan=5, padx=5, pady=(2, 0), sticky='w')

        self.progress_job.grid_remove()
        self.lbl_job_info.grid_remove()


        # Log and stats frame
        self.frm_logstats = ttk.LabelFrame(self, text="Log & Statistics", padding=(10, 10))
        stats_frame = ttk.Frame(self.frm_logstats)
        stats_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(stats_frame, text="Total Videos:", font=("Trebuchet MS", 10, "bold")).grid(row=0, column=0, sticky="e", padx=5)
        ttk.Label(stats_frame, textvariable=self.total_mp4).grid(row=0, column=1, sticky="w", padx=5)
        ttk.Label(stats_frame, text="Groups Remaining:", font=("Trebuchet MS", 10, "bold")).grid(row=0, column=2, sticky="e", padx=5)
        ttk.Label(stats_frame, textvariable=self.num_groups).grid(row=0, column=3, sticky="w", padx=5)
        ttk.Label(stats_frame, text="Groups Done:", font=("Trebuchet MS", 10, "bold")).grid(row=0, column=4, sticky="e", padx=5)
        ttk.Label(stats_frame, textvariable=self.groups_done).grid(row=0, column=5, sticky="w", padx=5)

        log_frame = ttk.Frame(self.frm_logstats)
        log_frame.pack(fill="both", expand=True)
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical")
        scrollbar.pack(side="right", fill="y")
        self.txt_log = tk.Text(
            log_frame, height=12, wrap="word", state="disabled", font=("Consolas", 11),
            bg="#1e1e1e", fg="#dcdcdc", borderwidth=1, relief="solid", insertbackground="#ffffff"
        )
        self.txt_log.pack(fill="both", expand=True)
        scrollbar.config(command=self.txt_log.yview)
        self.txt_log.tag_configure("link", foreground="#1E90FF", underline=True)

        self.main_video_volume_var.trace_add("write", self._update_main_video_volume_label)

    def _add_folder_row(self, label, var, row, parent, reload=False, bgm=False):
        lbl = ttk.Label(parent, text=label)
        lbl.grid(row=row, column=0, sticky="e", padx=5, pady=3)

        entry = ttk.Entry(parent, textvariable=var, width=50, font=("Trebuchet MS", 10))
        entry.grid(row=row, column=1, columnspan=2, sticky="we", padx=5, pady=3)
        self._add_right_click_menu(entry, [("ƒ?O Clear Path", lambda v=var: v.set(""))])

        btn = ttk.Button(parent, text="Browse", style="Secondary.TButton",
                        command=lambda: self._choose_folder(var, reload=reload, bgm=bgm))
        btn.grid(row=row, column=3, sticky="w", padx=5, pady=3)

        return (lbl, entry, btn)   # <-- TR §› V ¯? CA?C WIDGET

    def _layout(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=2)
        self.grid_columnconfigure(0, weight=1)
        self.frm_top.grid(row=0, column=0, sticky="nsew", padx=15, pady=(10, 5))
        self.frm_logstats.grid(row=1, column=0, sticky="nsew", padx=15, pady=(5, 10))
        self.frm_top.columnconfigure(0, weight=1)
        self.frm_logstats.columnconfigure(0, weight=1)
