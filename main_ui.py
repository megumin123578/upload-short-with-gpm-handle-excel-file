from imports import *


class MainUIMixin:
    def _build_shell(self):
        # container chính
        self._root_container = ttk.Frame(self)
        self._root_container.pack(fill="both", expand=True)

        # Sidebar
        self._sidebar = tk.Frame(self._root_container, width=220)
        self._sidebar.pack(side="left", fill="y")
        self._sidebar.pack_propagate(False)

        # Content
        self._content = ttk.Frame(self._root_container)
        self._content.pack(side="left", fill="both", expand=True)

        # Sidebar buttons
        self._nav_buttons = {}

        def add_btn(text, key, cmd):
            b = tk.Button(
                self._sidebar,
                text=text,
                anchor="w",
                relief="flat",
                pady=10,
                padx=12,
                font=("Segoe UI", 10, "bold"),
                command=lambda: (cmd(), self._highlight_nav(key)),
            )
            b.pack(fill="x")
            self._nav_buttons[key] = b

            # hover effect
            def on_enter(e, k=key):
                if getattr(self, "_active_nav_key", None) != k:
                    e.widget.configure(bg="#2AA50F")

            def on_leave(e, k=key):
                if getattr(self, "_active_nav_key", None) == k:
                    e.widget.configure(bg="#E6F0FF", fg="#000000")
                else:
                    e.widget.configure(bg=self._sidebar.cget("bg"), fg="#ffffff")

            b.bind("<Enter>", on_enter)
            b.bind("<Leave>", on_leave)

        add_btn("Auto Upload", "assign", lambda: self._show_page("assign"))
        add_btn("Concatenation", "concat", lambda: self._show_page("concat"))
        add_btn("Watch", "watch", lambda: self._show_page("watch"))

        # Status bar
        bar = ttk.Frame(self, relief=tk.SUNKEN, padding=6)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Label(bar, textvariable=self.status_var).pack(side=tk.LEFT)

    def _highlight_nav(self, active_key):
        self._active_nav_key = active_key
        for k, btn in self._nav_buttons.items():
            if k == active_key:
                btn.configure(bg="#E6F0FF", fg="#000000")
            else:
                btn.configure(bg=self._sidebar.cget("bg"), fg="#ffffff")

    def _ensure_page_built(self, key: str):
        if key in self.pages:
            return
        builder = self._lazy_page_builders.get(key)
        if builder:
            builder()

    def _show_page(self, key: str):
        self._ensure_page_built(key)
        for k, f in self.pages.items():
            f.pack_forget()
        if key in self.pages:
            self.pages[key].pack(fill="both", expand=True)
        self._highlight_nav(key)
