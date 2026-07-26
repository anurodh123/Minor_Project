# Disk Scheduling + Virtual File System Simulator

A PyQt6 desktop application that visualizes classic disk-scheduling algorithms and pairs them with a small in-memory virtual file system (VFS) you can interact with through a command console. Reading a "file" in the VFS triggers a real disk-scheduling simulation against that file's allocated blocks, so you can see how different algorithms would service the same I/O request.

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![PyQt6](https://img.shields.io/badge/GUI-PyQt6-41cd52)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

## Features

### Disk Scheduler tab
- Six classic disk-scheduling algorithms: **FCFS, SSTF, SCAN, C-SCAN, LOOK, C-LOOK**
- Configurable disk size, initial head position, request queue, and head direction (**left**/**right**)
- Run a single algorithm or compare all six side by side
- A results table showing total head movement (seek distance) per algorithm
- Matplotlib visualizations of the head's movement trace, including a highlighted starting position and initial direction of travel
- Automatic identification of the best-performing algorithm when comparing all six

### Virtual File System tab
- A lightweight in-memory file system with directories, files, and block-level allocation
- A live directory tree view alongside a terminal-style console
- Familiar commands: `pwd`, `ls`, `mkdir`, `cd`, `touch`, `write`, `cat`, `rm`, `tree`, `diskmap`, `format`, `clear`, `help`
- `cat <file>` "reads" a file by servicing its allocated blocks with the currently selected disk-scheduling algorithm — switch to the Disk Scheduler tab to see the resulting trace
- `cat <file> --all` compares all six algorithms against that file's blocks in one go
- A visual free/used block bitmap (`diskmap`) and full directory tree printout (`tree`)


## Requirements

- Python 3.9+
- [PyQt6](https://pypi.org/project/PyQt6/)
- [Matplotlib](https://pypi.org/project/matplotlib/)

## Installation

```bash
# Clone the repository
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>

# (Recommended) create a virtual environment
python -m venv venv
source venv/bin/activate      # On Windows: venv\Scripts\activate

# Install dependencies
pip install PyQt6 matplotlib
```

Alternatively, if a `requirements.txt` is included:

```bash
pip install -r requirements.txt
```

## Usage

Run the application with:

```bash
python try.py
```

### Disk Scheduler tab

1. Enter the disk size (number of cylinders), the initial head position, and a comma-separated request queue.
2. Choose a head direction — **Left** (toward lower cylinders) or **Right** (toward higher cylinders) — used by the SCAN-family algorithms.
3. Select an algorithm from the dropdown and click **Run Selected Algorithm**, or click **Compare All Algorithms** to run all six at once.
4. Review the service order, total head movement, and movement direction in the summary panel, the results table, and the plotted head-movement trace.

### Virtual File System tab

Type commands into the console input at the bottom of the tab:

```text
mkdir docs
cd docs
touch notes.txt 3
write notes.txt Hello from the virtual file system!
cat notes.txt
cat notes.txt --all
tree
diskmap
```

Reading a file with `cat` automatically switches to the Disk Scheduler tab and populates the request queue with that file's allocated blocks, then runs the simulation using the currently selected algorithm (or all six with `--all`).

Run `help` at any time to see the full command list.

## Project Structure

```text
.
├── disk_scheduler.py   # Main application (algorithms, VFS, and PyQt6 UI)
└── README.md
```

## How It Works

- **Algorithms** are implemented as plain functions that take a request list, head position, disk size, and direction, and return the service order, total head movement, and the full physical head path (including boundary bounces for SCAN/C-SCAN).
- **The VFS** allocates disk "blocks" for each file using a simple first-fit strategy over a free-block bitmap, growing a file's allocation as its content grows.
- **The bridge between the two**: reading a file collects its block numbers and feeds them into the disk-scheduler simulation as the request queue, so scheduling behavior can be observed against realistic, allocation-driven workloads instead of only manually entered numbers.

## Contributing

Contributions are welcome! Feel free to open an issue or submit a pull request for bug fixes, new algorithms, or UI improvements.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -m "Add my feature"`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Open a pull request

## License

This project is licensed under the [MIT License](LICENSE).
