import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import shlex

from dataclasses import dataclass, field
def anurodh():
    def fcfs(requests, head, **kwargs):
        order = list(requests)
        path = [head] + order
        total = sum(
            abs(path[index + 1] - path[index])
            for index in range(len(path) - 1)
        )
        return order, total, path


    def sstf(requests, head, **kwargs):
        pending = list(requests)
        order = []
        path = [head]
        current = head
        total = 0

        while pending:
            nearest = min(
                pending,
                key=lambda request: abs(request - current)
            )

            total += abs(nearest - current)
            current = nearest

            order.append(nearest)
            path.append(nearest)
            pending.remove(nearest)

        return order, total, path


    def scan(
        requests,
        head,
        disk_size=200,
        direction="right",
        **kwargs
    ):
        sorted_requests = sorted(requests)

        upper = [
            request
            for request in sorted_requests
            if request >= head
        ]

        lower = [
            request
            for request in sorted_requests
            if request < head
        ]

        if direction == "right":
            path = (
                upper
                + [disk_size - 1]
                + list(reversed(lower))
            )
        else:
            path = (
                list(reversed(lower))
                + [0]
                + upper
            )

        order = []
        full_path = [head]
        current = head
        total = 0

        for position in path:
            total += abs(position - current)
            current = position
            full_path.append(position)

            if position in requests:
                order.append(position)

        return order, total, full_path


    def c_scan(
        requests,
        head,
        disk_size=200,
        direction="right",
        **kwargs
    ):
        sorted_requests = sorted(requests)

        upper = [
            request
            for request in sorted_requests
            if request >= head
        ]

        lower = [
            request
            for request in sorted_requests
            if request < head
        ]

        if direction == "right":
            path = (
                upper
                + [disk_size - 1, 0]
                + lower
            )
        else:
            path = (
                list(reversed(lower))
                + [0, disk_size - 1]
                + list(reversed(upper))
            )

        order = []
        full_path = [head]
        current = head
        total = 0

        for position in path:
            total += abs(position - current)
            current = position
            full_path.append(position)

            if position in requests:
                order.append(position)

        return order, total, full_path


    def look(
        requests,
        head,
        direction="right",
        **kwargs
    ):
        sorted_requests = sorted(requests)

        upper = [
            request
            for request in sorted_requests
            if request >= head
        ]

        lower = [
            request
            for request in sorted_requests
            if request < head
        ]

        if direction == "right":
            path = upper + list(reversed(lower))
        else:
            path = list(reversed(lower)) + upper

        order = []
        full_path = [head]
        current = head
        total = 0

        for position in path:
            total += abs(position - current)
            current = position
            full_path.append(position)
            order.append(position)

        return order, total, full_path


    def c_look(
        requests,
        head,
        direction="right",
        **kwargs
    ):
        sorted_requests = sorted(requests)

        upper = [
            request
            for request in sorted_requests
            if request >= head
        ]

        lower = [
            request
            for request in sorted_requests
            if request < head
        ]

        if direction == "right":
            path = upper + lower
        else:
            path = (
                list(reversed(lower))
                + list(reversed(upper))
            )

        order = []
        full_path = [head]
        current = head
        total = 0

        for position in path:
            total += abs(position - current)
            current = position
            full_path.append(position)
            order.append(position)

        return order, total, full_path


    ALGORITHMS = {
        "FCFS": fcfs,
        "SSTF": sstf,
        "SCAN": scan,
        "C-SCAN": c_scan,
        "LOOK": look,
        "C-LOOK": c_look
    }


    def movement_direction(path):
        if not path:
            return "No head movement."

        if len(path) < 2:
            return (
                f"Head at cylinder {path[0]} — "
                "no requests to service."
            )

        head = path[0]
        first_position = path[1]

        if first_position > head:
            return (
                f"Head at cylinder {head} → "
                "moving right toward higher cylinders."
            )

        if first_position < head:
            return (
                f"Head at cylinder {head} ← "
                "moving left toward lower cylinders."
            )

        return (
            f"Head at cylinder {head} • "
            "no initial movement."
        )


    # ============================================================
    # Virtual file system
    # ============================================================

    UNIT_CHARS_PER_BLOCK = 8


    HELP_TEXT = """Available commands:

    pwd
        Show the current directory.

    ls
        List the contents of the current directory.

    mkdir <name>
        Create a subdirectory.

    cd <name|..|/>
        Change directory.

    touch <name> [blocks]
        Create an empty file.

    write <name> <text...>
        Write text to a file.

    cat <name>
        Read a file and simulate disk access.

    cat <name> --all
        Read a file and compare all disk algorithms.

    rm <name>
        Delete an empty directory or file.

    tree
        Print the complete directory tree.

    diskmap
        Show the free/used block bitmap.

    format [size]
        Erase everything and format the disk.

    clear
        Clear the virtual console.

    help
        Show this help message.
    """


    class VFSError(Exception):
        pass


    @dataclass
    class VFSNode:
        name: str
        is_dir: bool = True
        parent: object = None
        children: dict = field(default_factory=dict)
        blocks: list = field(default_factory=list)
        content: str = ""


    class VirtualFileSystem:

        def __init__(self, disk_size=200):
            self.disk_size = disk_size
            self.free_bitmap = [True] * disk_size
            self.root = VFSNode(
                name="/",
                is_dir=True,
                parent=None
            )
            self.cwd = self.root

        def _find_free_blocks(self, count):
            if count <= 0:
                return []

            run_start = None
            run_length = 0

            for index, is_free in enumerate(self.free_bitmap):
                if is_free:
                    if run_start is None:
                        run_start = index

                    run_length += 1

                    if run_length == count:
                        return list(
                            range(
                                run_start,
                                run_start + count
                            )
                        )
                else:
                    run_start = None
                    run_length = 0

            scattered = [
                index
                for index, is_free in enumerate(
                    self.free_bitmap
                )
                if is_free
            ]

            if len(scattered) >= count:
                return scattered[:count]

            return None

        def path_string(self):
            parts = []
            current = self.cwd

            while current.parent is not None:
                parts.append(current.name)
                current = current.parent

            if not parts:
                return "/"

            return "/" + "/".join(reversed(parts))

        def cd(self, name):
            if name == "..":
                if self.cwd.parent is not None:
                    self.cwd = self.cwd.parent
                return

            if name in ("", "/"):
                self.cwd = self.root
                return

            target = self.cwd.children.get(name)

            if target is None or not target.is_dir:
                raise VFSError(
                    f"No such directory: {name}"
                )

            self.cwd = target

        def mkdir(self, name):
            if not name:
                raise VFSError(
                    "Directory name cannot be empty."
                )

            if name in self.cwd.children:
                raise VFSError(
                    f"'{name}' already exists."
                )

            self.cwd.children[name] = VFSNode(
                name=name,
                is_dir=True,
                parent=self.cwd
            )

        def touch(self, name, block_count=1):
            if not name:
                raise VFSError(
                    "File name cannot be empty."
                )

            if name in self.cwd.children:
                raise VFSError(
                    f"'{name}' already exists."
                )

            if block_count <= 0:
                raise VFSError(
                    "Block count must be greater than zero."
                )

            blocks = self._find_free_blocks(block_count)

            if blocks is None:
                raise VFSError(
                    "Not enough free disk space."
                )

            for block in blocks:
                self.free_bitmap[block] = False

            node = VFSNode(
                name=name,
                is_dir=False,
                parent=self.cwd,
                blocks=blocks,
                content=""
            )

            self.cwd.children[name] = node
            return node

        def write(self, name, text):
            node = self.cwd.children.get(name)

            if node is None or node.is_dir:
                raise VFSError(
                    f"No such file: {name}"
                )

            required_blocks = max(
                1,
                (len(text) + UNIT_CHARS_PER_BLOCK - 1)
                // UNIT_CHARS_PER_BLOCK
            )

            if required_blocks > len(node.blocks):
                additional_count = (
                    required_blocks - len(node.blocks)
                )

                additional_blocks = self._find_free_blocks(
                    additional_count
                )

                if additional_blocks is None:
                    raise VFSError(
                        "Not enough free disk space "
                        "to grow this file."
                    )

                for block in additional_blocks:
                    self.free_bitmap[block] = False

                node.blocks.extend(additional_blocks)

            node.content = text
            return node

        def read(self, name):
            node = self.cwd.children.get(name)

            if node is None or node.is_dir:
                raise VFSError(
                    f"No such file: {name}"
                )

            return node

        def rm(self, name):
            node = self.cwd.children.get(name)

            if node is None:
                raise VFSError(
                    f"No such file or directory: {name}"
                )

            if node.is_dir and node.children:
                raise VFSError(
                    f"Directory '{name}' is not empty."
                )

            for block in node.blocks:
                self.free_bitmap[block] = True

            del self.cwd.children[name]

        def ls(self):
            return sorted(
                self.cwd.children.items(),
                key=lambda item: item[0].lower()
            )

        def tree_string(self):
            lines = ["/"]

            def walk(node, prefix):
                children = sorted(
                    node.children.items(),
                    key=lambda item: item[0].lower()
                )

                for index, (name, child) in enumerate(children):
                    is_last = index == len(children) - 1
                    connector = "└── " if is_last else "├── "

                    if child.is_dir:
                        lines.append(
                            f"{prefix}{connector}{name}/"
                        )

                        extension = (
                            "    "
                            if is_last
                            else "│   "
                        )

                        walk(
                            child,
                            prefix + extension
                        )
                    else:
                        lines.append(
                            f"{prefix}{connector}{name} "
                            f"(blocks: {child.blocks})"
                        )

            walk(self.root, "")
            return "\n".join(lines)

        def diskmap_string(self):
            return "".join(
                "░" if is_free else "█"
                for is_free in self.free_bitmap
            )

        def format(self, size):
            if size <= 0:
                raise VFSError(
                    "Disk size must be greater than zero."
                )

            self.disk_size = size
            self.free_bitmap = [True] * size
            self.root = VFSNode(
                name="/",
                is_dir=True,
                parent=None
            )
            self.cwd = self.root

        def used_blocks(self):
            return sum(
                not is_free
                for is_free in self.free_bitmap
            )

        def free_blocks(self):
            return sum(
                is_free
                for is_free in self.free_bitmap
            )
        
    def draw_disk_trace(
        algorithm_name,
        path,
        disk_size,
        total_movement
    ):
        if not path:
            st.info("No disk movement to display.")
            return

        figure, axis = plt.subplots(
            figsize=(10, 4)
        )

        service_order = list(range(len(path)))

        axis.plot(
            path,
            service_order,
            marker="o",
            linewidth=2,
            color="#2F5597"
        )

        for index, cylinder in enumerate(path):
            axis.annotate(
                str(cylinder),
                (cylinder, index),
                textcoords="offset points",
                xytext=(0, 8),
                ha="center",
                fontsize=9
            )

        head = path[0]

        axis.plot(
            head,
            0,
            marker="o",
            markersize=12,
            markerfacecolor="none",
            markeredgecolor="#C0392B",
            markeredgewidth=2
        )

        if len(path) > 1:
            direction = 1 if path[1] >= head else -1

            axis.annotate(
                "",
                xy=(
                    head + direction * disk_size * 0.06,
                    0
                ),
                xytext=(head, 0),
                arrowprops={
                    "arrowstyle": "-|>",
                    "color": "#C0392B",
                    "lw": 2
                }
            )

        axis.annotate(
            f"Head start: {head}",
            (head, 0),
            textcoords="offset points",
            xytext=(0, -18),
            ha="center",
            fontsize=9,
            color="#C0392B",
            fontweight="bold"
        )

        axis.set_title(
            f"Head Movement Trace — {algorithm_name} "
            f"(Total: {total_movement})",
            fontsize=12
        )

        axis.set_xlabel("Cylinder")
        axis.set_ylabel("Service Order")

        axis.set_xlim(
            -disk_size * 0.03,
            disk_size * 1.03
        )

        axis.invert_yaxis()
        axis.grid(
            True,
            linestyle="--",
            alpha=0.5
        )

        figure.tight_layout()
        st.pyplot(figure)

        plt.close(figure)


    def parse_disk_inputs(
        disk_size_text,
        head_text,
        requests_text
    ):
        try:
            disk_size = int(disk_size_text)
            head = int(head_text)

            requests = [
                int(value.strip())
                for value in requests_text.split(",")
                if value.strip()
            ]

        except ValueError:
            raise ValueError(
                "Disk size, head position, and requests "
                "must contain integers."
            )

        if disk_size <= 0:
            raise ValueError(
                "Disk size must be greater than zero."
            )

        if not requests:
            raise ValueError(
                "The request queue cannot be empty."
            )

        if head < 0 or head >= disk_size:
            raise ValueError(
                f"Head must be between 0 and {disk_size - 1}."
            )

        for request in requests:
            if request < 0 or request >= disk_size:
                raise ValueError(
                    f"Request {request} is outside the valid "
                    f"range 0 to {disk_size - 1}."
                )

        return disk_size, head, requests


    def render_disk_results(
        results,
        disk_size
    ):
        if not results:
            return

        result_rows = []

        for algorithm_name, result in results.items():
            order, total, path = result

            result_rows.append(
                {
                    "Algorithm": algorithm_name,
                    "Service Order": ", ".join(
                        str(value)
                        for value in order
                    ),
                    "Total Head Movement": total,
                    "Initial Direction": movement_direction(path)
                }
            )

        result_frame = pd.DataFrame(result_rows)

        st.dataframe(
            result_frame,
            use_container_width=True,
            hide_index=True
        )

        best_algorithm = min(
            results,
            key=lambda name: results[name][1]
        )

        best_total = results[best_algorithm][1]

        st.success(
            f"Best result: {best_algorithm} "
            f"with {best_total} cylinders of movement."
        )


    def render_vfs_tree(node, prefix=""):
        lines = []

        children = sorted(
            node.children.items(),
            key=lambda item: item[0].lower()
        )

        for index, (name, child) in enumerate(children):
            is_last = index == len(children) - 1

            connector = (
                "└── "
                if is_last
                else "├── "
            )

            if child.is_dir:
                lines.append(
                    f"{prefix}{connector}📁 {name}/"
                )

                extension = (
                    "    "
                    if is_last
                    else "│   "
                )

                lines.extend(
                    render_vfs_tree(
                        child,
                        prefix + extension
                    )
                )

            else:
                lines.append(
                    f"{prefix}{connector}📄 {name} "
                    f"(blocks: {child.blocks})"
                )

        return lines


    def vfs_tree_text(vfs):
        lines = ["/"]
        lines.extend(
            render_vfs_tree(
                vfs.root
            )
        )
        return "\n".join(lines)


    def simulate_file_access(
        vfs,
        file_name,
        algorithm_name,
        disk_size,
        head,
        direction
    ):
        node = vfs.read(file_name)

        if not node.blocks:
            return (
                f"'{file_name}' has no allocated blocks."
            )

        requests = node.blocks

        algorithm = ALGORITHMS[algorithm_name]

        order, total, path = algorithm(
            requests,
            head,
            disk_size=disk_size,
            direction=direction
        )

        return {
            "file_name": file_name,
            "requests": requests,
            "order": order,
            "total": total,
            "path": path,
            "algorithm": algorithm_name
        }


    def execute_vfs_command(
        command_text,
        vfs,
        disk_size,
        head,
        direction,
        algorithm_name
    ):
        command_text = command_text.strip()

        if not command_text:
            return ""

        try:
            parts = shlex.split(command_text)
        except ValueError as error:
            return f"Command parsing error: {error}"

        if not parts:
            return ""

        command = parts[0].lower()
        arguments = parts[1:]

        try:
            if command == "help":
                return HELP_TEXT

            if command == "pwd":
                return vfs.path_string()

            if command == "ls":
                entries = vfs.ls()

                if not entries:
                    return "(empty directory)"

                output = []

                for name, node in entries:
                    if node.is_dir:
                        output.append(
                            f"[DIR]  {name}"
                        )
                    else:
                        output.append(
                            f"[FILE] {name} "
                            f"blocks={node.blocks}"
                        )

                return "\n".join(output)

            if command == "mkdir":
                if len(arguments) != 1:
                    return "Usage: mkdir <name>"

                vfs.mkdir(arguments[0])

                return (
                    f"Directory '{arguments[0]}' created."
                )

            if command == "cd":
                if len(arguments) != 1:
                    return "Usage: cd <name|..|/>"

                vfs.cd(arguments[0])

                return (
                    f"Current directory: "
                    f"{vfs.path_string()}"
                )

            if command == "touch":
                if len(arguments) < 1:
                    return "Usage: touch <name> [blocks]"

                file_name = arguments[0]
                block_count = 1

                if len(arguments) >= 2:
                    block_count = int(arguments[1])

                node = vfs.touch(
                    file_name,
                    block_count
                )

                return (
                    f"File '{file_name}' created. "
                    f"Allocated blocks: {node.blocks}"
                )

            if command == "write":
                if len(arguments) < 2:
                    return "Usage: write <name> <text...>"

                file_name = arguments[0]
                content = " ".join(arguments[1:])

                node = vfs.write(
                    file_name,
                    content
                )

                return (
                    f"Wrote {len(content)} characters to "
                    f"'{file_name}'. Blocks: {node.blocks}"
                )

            if command in ("cat", "read"):
                if len(arguments) < 1:
                    return (
                        "Usage: cat <name> "
                        "[--all]"
                    )

                file_name = arguments[0]
                compare_all = "--all" in arguments

                if compare_all:
                    output = []

                    for name, algorithm in ALGORITHMS.items():
                        node = vfs.read(file_name)

                        order, total, path = algorithm(
                            node.blocks,
                            head,
                            disk_size=disk_size,
                            direction=direction
                        )

                        output.append(
                            f"{name}: {total} cylinders"
                        )

                    return (
                        f"File: {file_name}\n"
                        f"Content: {vfs.read(file_name).content}\n"
                        f"Disk access comparison:\n"
                        + "\n".join(output)
                    )

                node = vfs.read(file_name)

                order, total, path = ALGORITHMS[
                    algorithm_name
                ](
                    node.blocks,
                    head,
                    disk_size=disk_size,
                    direction=direction
                )

                st.session_state.vfs_last_access = {
                    "file_name": file_name,
                    "content": node.content,
                    "order": order,
                    "total": total,
                    "path": path,
                    "algorithm": algorithm_name,
                    "disk_size": disk_size
                }

                return (
                    f"File: {file_name}\n"
                    f"Content: {node.content}\n"
                    f"Blocks: {node.blocks}\n"
                    f"Algorithm: {algorithm_name}\n"
                    f"Total movement: {total} cylinders"
                )

            if command == "rm":
                if len(arguments) != 1:
                    return "Usage: rm <name>"

                vfs.rm(arguments[0])

                return (
                    f"'{arguments[0]}' removed."
                )

            if command == "tree":
                return vfs_tree_text(vfs)

            if command == "diskmap":
                used = vfs.used_blocks()
                free = vfs.free_blocks()

                return (
                    f"Used blocks: {used}\n"
                    f"Free blocks: {free}\n"
                    f"█ = used, ░ = free\n\n"
                    f"{vfs.diskmap_string()}"
                )

            if command == "format":
                size = disk_size

                if arguments:
                    size = int(arguments[0])

                vfs.format(size)

                return (
                    f"Disk formatted with {size} blocks. "
                    "All files were erased."
                )

            if command == "clear":
                st.session_state.vfs_console = []
                return ""

            return (
                f"Unknown command: '{command}'. "
                "Type 'help' for available commands."
            )

        except VFSError as error:
            return f"Error: {error}"

        except ValueError:
            return (
                "Error: an argument requiring a number "
                "was invalid."
            )


    def disk_module():
        st.markdown(
            
            """
            <style>
            .disk-title {
                color: #3498db;
                font-size: 30px;
                font-weight: bold;
            }

            .vfs-console {
                background-color: #1e1e1e;
                color: #d4d4d4;
                padding: 15px;
                border-radius: 8px;
                font-family: Consolas, monospace;
                white-space: pre-wrap;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            '<div class="disk-title">'
            'VFS & Disk Scheduling Simulator'
            '</div>',
            unsafe_allow_html=True
        )

        st.caption(
            "Explore disk head scheduling and a "
            "simulated virtual file system."
        )

        if "vfs_object" not in st.session_state:
            st.session_state.vfs_object = (
                VirtualFileSystem(200)
            )

        if "vfs_console" not in st.session_state:
            st.session_state.vfs_console = [
                "Virtual File System ready.",
                "Type 'help' for available commands."
            ]

        vfs = st.session_state.vfs_object

        scheduler_tab, filesystem_tab = st.tabs(
            [
                "Disk Scheduler",
                "Virtual File System"
            ]
        )

        with scheduler_tab:
            st.subheader("Simulation Parameters")

            left_column, right_column = st.columns(2)

            with left_column:
                disk_size_input = st.number_input(
                    "Disk size (cylinders)",
                    min_value=1,
                    max_value=10000,
                    value=vfs.disk_size,
                    step=1,
                    key="disk_size_input"
                )

                head_input = st.number_input(
                    "Initial head position",
                    min_value=0,
                    value=53,
                    step=1,
                    key="disk_head_input"
                )

            with right_column:
                requests_input = st.text_input(
                    "Request queue",
                    value="98, 183, 37, 122, 14, 124, 65, 67",
                    key="disk_requests_input"
                )

                direction_label = st.radio(
                    "Direction",
                    [
                        "Right (higher cylinders)",
                        "Left (lower cylinders)"
                    ],
                    horizontal=True,
                    key="disk_direction_input"
                )

            direction = (
                "right"
                if direction_label.startswith("Right")
                else "left"
            )

            algorithm_name = st.selectbox(
                "Algorithm",
                list(ALGORITHMS.keys()),
                key="disk_algorithm_input"
            )

            run_column, compare_column = st.columns(2)

            with run_column:
                run_selected = st.button(
                    "Run Selected Algorithm",
                    type="primary",
                    use_container_width=True,
                    key="run_disk_algorithm"
                )

            with compare_column:
                compare_all = st.button(
                    "Compare All Algorithms",
                    use_container_width=True,
                    key="compare_disk_algorithms"
                )

            if run_selected or compare_all:
                try:
                    disk_size, head, requests = (
                        parse_disk_inputs(
                            str(disk_size_input),
                            str(head_input),
                            requests_input
                        )
                    )

                    if run_selected:
                        algorithm = ALGORITHMS[
                            algorithm_name
                        ]

                        order, total, path = algorithm(
                            requests,
                            head,
                            disk_size=disk_size,
                            direction=direction
                        )

                        st.session_state.disk_results = {
                            algorithm_name: (
                                order,
                                total,
                                path
                            )
                        }

                    else:
                        results = {}

                        for name, algorithm in ALGORITHMS.items():
                            results[name] = algorithm(
                                requests,
                                head,
                                disk_size=disk_size,
                                direction=direction
                            )

                        st.session_state.disk_results = results

                except ValueError as error:
                    st.error(str(error))

            disk_results = st.session_state.get(
                "disk_results"
            )

            if disk_results:
                render_disk_results(
                    disk_results,
                    int(disk_size_input)
                )

                st.subheader("Head Movement Visualization")

                if len(disk_results) == 1:
                    name, result = next(
                        iter(disk_results.items())
                    )

                    order, total, path = result

                    st.write(
                        f"**{name} service order:** "
                        f"{order}"
                    )

                    st.write(
                        movement_direction(path)
                    )

                    draw_disk_trace(
                        name,
                        path,
                        int(disk_size_input),
                        total
                    )

                else:
                    selected_chart = st.selectbox(
                        "View trace for",
                        list(disk_results.keys()),
                        key="disk_chart_algorithm"
                    )

                    order, total, path = (
                        disk_results[selected_chart]
                    )

                    draw_disk_trace(
                        selected_chart,
                        path,
                        int(disk_size_input),
                        total
                    )

        with filesystem_tab:
            st.subheader("Virtual File System")

            filesystem_left, filesystem_right = (
                st.columns([1, 2])
            )

            with filesystem_left:
                st.write(
                    f"Current directory: "
                    f"`{vfs.path_string()}`"
                )

                st.code(
                    vfs_tree_text(vfs),
                    language="text"
                )

                st.metric(
                    "Used Blocks",
                    vfs.used_blocks()
                )

                st.metric(
                    "Free Blocks",
                    vfs.free_blocks()
                )

            with filesystem_right:
                st.write("Terminal Console")

                console_text = "\n".join(
                    st.session_state.vfs_console
                )

                st.code(
                    console_text,
                    language="text"
                )

                with st.form(
                    "vfs_command_form",
                    clear_on_submit=True
                ):
                    command_input = st.text_input(
                        "Enter a command",
                        placeholder="Type help for commands"
                    )

                    execute_command = st.form_submit_button(
                        "Execute Command",
                        use_container_width=True
                    )

                if execute_command and command_input.strip():
                    disk_size = int(
                        st.session_state.get(
                            "disk_size_input",
                            vfs.disk_size
                        )
                    )

                    head = int(
                        st.session_state.get(
                            "disk_head_input",
                            53
                        )
                    )

                    direction = st.session_state.get(
                        "disk_direction_input",
                        "Right (higher cylinders)"
                    )

                    direction = (
                        "right"
                        if direction.startswith("Right")
                        else "left"
                    )

                    algorithm_name = st.session_state.get(
                        "disk_algorithm_input",
                        "FCFS"
                    )

                    st.session_state.vfs_console.append(
                        f"{vfs.path_string()} $ "
                        f"{command_input}"
                    )

                    output = execute_vfs_command(
                        command_input,
                        vfs,
                        disk_size,
                        head,
                        direction,
                        algorithm_name
                    )

                    if output:
                        st.session_state.vfs_console.append(
                            output
                        )

                    st.rerun()

            last_access = st.session_state.get(
                "vfs_last_access"
            )

            if last_access:
                st.divider()
                st.subheader("Last File Access Trace")

                st.write(
                    f"File: `{last_access['file_name']}`"
                )

                st.write(
                    f"Algorithm: `{last_access['algorithm']}`"
                )

                st.write(
                    f"Total movement: "
                    f"`{last_access['total']} cylinders`"
                )

                draw_disk_trace(
                    last_access["algorithm"],
                    last_access["path"],
                    last_access["disk_size"],
                    last_access["total"]
                )
    disk_module()
