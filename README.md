
<p align="center">
  <img src="./logo.png" alt="CameraFile Logo" width="150">
</p>

---

[![Build Status](https://github.com/dpjl/cfm/actions/workflows/linux.yml/badge.svg)](https://github.com/dpjl/cfm/actions/workflows/linux.yml)
[![Build Status](https://github.com/dpjl/cfm/actions/workflows/windows.yml/badge.svg)](https://github.com/dpjl/cfm/actions/workflows/linux.yml)
[![Build Status](https://github.com/dpjl/cfm/actions/workflows/macos.yml/badge.svg)](https://github.com/dpjl/cfm/actions/workflows/macos.yml)
[![Build Status](https://github.com/dpjl/cfm/actions/workflows/docker.yml/badge.svg)](https://github.com/dpjl/cfm/actions/workflows/docker.yml)
[![Test Coverage](https://img.shields.io/codecov/c/github/dpjl/cfm)](https://codecov.io/gh/dpjl/cfm)
[![License](https://img.shields.io/github/license/dpjl/cfm)](./LICENSE)
[![Latest Release](https://img.shields.io/github/v/release/yourusername/camerafile)](https://github.com/yourusername/camerafile/releases)
[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/downloads/)
[![Contributions Welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)](https://github.com/yourusername/camerafile/issues)

---

## 📸 CFM (Camera Files Manager)

**CFM** is an efficient CLI tool designed to organize your photo and video collections based on their actual origin, such as the camera model or apps like WhatsApp. It leverages metadata analysis and effectively manages large photo and video libraries.

---

## ✨ Key Features

- 🗃️ **Intelligent Organization**: Automatically organizes files by camera model, date, media type, and more.
- 🎬 **Video Support**: Supports organization for videos even when they lack EXIF metadata.
- 🪝 **Hard Links Usage**: Creates organized \"views\" without duplicating files, ensuring zero extra disk usage.
- 📦 **ZIP Extraction**: Reads and organizes media directly from within ZIP archive files.
- 📑 **Duplicate Detection**: Simple yet efficient detection of duplicate files.
- 🔍 **Gallery Comparison**: Precise comparison between two media galleries to identify common media or duplicates.
- 🌐 **Powerful React UI**: Visualize two galleries side-by-side, providing an interactive way to inspect duplicate detection results, organization structures, and common media files.

---

## 🚀 Installation

### Prerequisites

- **Python 3.12** or newer
- **pip** installed

### Source Installation

```bash
git clone https://github.com/yourusername/cfm.git
cd cfm
pip install -r requirements.txt
```

### Pre-built Executables

Visit the [Releases](https://github.com/yourusername/cfm/releases) page to download the executable for your system:

- **Windows**: `cfm.windows-amd64.exe`
- **Linux**: `cfm.linux-amd64`
- **macOS**: `cfm.mac-amd64`

Make the file executable on Linux or macOS:

```bash
chmod +x cfm.linux-amd64 # or cfm.mac-amd64
```

---

## 💡 Usage Examples

### Organize Media Files

Organize your files automatically by metadata:

```bash
cfm organize --source /path/to/source --destination /path/to/destination
```

By default, files are organized into directories based on the camera model, using hard links.

### Generate Thumbnails

```bash
cfm generate-thumbnails --source /path/to/files --output /path/to/thumbnails
```

### Detect and Compare Duplicates

Detect duplicates and compare two media galleries:

```bash
cfm detect-duplicates --source /path/to/gallery1 --compare /path/to/gallery2
```

---

## 🧪 Testing

Run unit tests with coverage:

```bash
pytest --cov=cfm tests/
```

---

## 🤝 Contributing

Contributions are welcome! To contribute:

1. Fork this repository
2. Create your feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes
4. Submit a Pull Request

Check out our [contribution guide](CONTRIBUTING.md) for more details.

---

## ❤️ Support the Project

If you find this tool useful, consider supporting its development:

- [Donate via PayPal](https://paypal.me/yourusername)
- [Sponsor via GitHub Sponsors](https://github.com/sponsors/yourusername)

---

## 📄 License

This project is licensed under the **GPL-3.0 License**. See the [LICENSE](./LICENSE) file for more details.

