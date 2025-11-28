# reindenter

### ✔ Corrected Description for Your New Ef-Reindenter (v2.0+)

**Ef-Reindenter** is an advanced Python code reindentation and light-refactoring tool with a full GUI.
It repairs indentation, organizes imports, applies PEP 8 formatting, and includes safe AST-aware refactor features.

Unlike the older minimal edition, this version includes a **smart structural “healer”** that can fix badly-broken indentation *even when the code does not parse*, and then reindent cleanly.

---

### ✔ Correct Version (You can paste this in GitHub)

# **Ef-Reindenter**

Python Code Reindenter & Formatter (GUI, PEP 8, Structural Repair)

**Ef-Reindenter** is a graphical Python formatting tool that repairs indentation, fixes broken block structure, formats code to PEP 8, organizes imports, and applies safe refactor transformations.
It is the enhanced successor to the legacy “Python Reindenter” tool.

## **Features**

* **Smart Reindentation** – Applies consistent indentation (default 4 spaces) using a corrected logic engine.
* **Structural Repair Layer** – Fixes misaligned `else/elif/except`, stray `return` lines, broken method indentation, and other block-level damage before reindenting.
* **Works Even on Broken Code** – `Apply Indent` no longer requires valid syntax; it can clean up heavily malformed files.
* **PEP 8 Formatter** – Normalizes whitespace, comments, blank lines, operator spacing, and long lines.
* **Import Organizer** – Groups and sorts stdlib, third-party, and local imports.
* **Safe Refactor Tools** – Remove unused imports, simplify boolean returns, convert simple `.format()` and `%` strings to f-strings.
* **File Load & Save** – Clean GUI workflow for loading, reformatting, and saving Python files.

## **How It Works**

1. Load a `.py` file into the GUI.
2. (Optional) Reset indentation or start directly.
3. Apply:

   * **Apply Indent** → fixes and reindents (works even with SyntaxErrors).
   * **PEP 8 Format** → full AST-safe formatting pipeline.
   * **Organize Imports** → restructures import blocks.
   * **Refactor Tools** → safe transformations.
4. Save the result.

## **When to Use It**

* Cleaning up inconsistent indentation
* Fixing broken or pasted code
* Preparing code for review
* Reformatting legacy scripts
* Quickly organizing imports or simplifying logic

## **License**

Released under **GPL-3.0** (matching your header conventions).
