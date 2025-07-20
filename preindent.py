import tkinter as tk
from tkinter import filedialog, messagebox
import re

class PythonReindenterApp:
    """
    GUI application for reindenting Python source files using Tkinter.
    """
    def __init__(self, root):
        self.root = root
        self.root.title("Python Reindenter")

        # State variables
        self.filename = None
        self.indentation_applied = False
        self.version = "1.3" # Updated version for enhancements
        self.indent_spaces_var = tk.IntVar(value=4) # Default to 4 spaces

        # Layout
        self.create_menu()
        self.text_display = tk.Text(self.root, wrap="none", state="disabled", font=("Courier", 12))
        self.text_display.pack(expand=True, fill="both")

        self.status_label = tk.Label(self.root, text="Welcome to Python Reindenter", anchor="w")
        self.status_label.pack(fill="x")

    def create_menu(self):
        menubar = tk.Menu(self.root)

        # File Menu
        self.file_menu = tk.Menu(menubar, tearoff=0)
        self.file_menu.add_command(label="Load", command=self.load_file)
        self.file_menu.add_command(label="Save", command=self.save_file, state="disabled")
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Quit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=self.file_menu)

        # Edit Menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Reset Indentation", command=self.reset_indentation)

        # New: Indentation Spaces Submenu
        indent_menu = tk.Menu(edit_menu, tearoff=0)
        indent_menu.add_radiobutton(label="2 Spaces", variable=self.indent_spaces_var, value=2,
                                    command=self.update_indent_spaces_setting)
        indent_menu.add_radiobutton(label="4 Spaces", variable=self.indent_spaces_var, value=4,
                                    command=self.update_indent_spaces_setting)
        edit_menu.add_cascade(label="Set Indent Spaces", menu=indent_menu)

        edit_menu.add_command(label="Apply Indent", command=self.apply_indent_from_menu)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        # Help Menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)

    def load_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Python Files", "*.py")])
        if file_path:
            self.filename = file_path
            with open(self.filename, 'r') as file:
                code = file.read()
            self.display_code(code)
            self.indentation_applied = False
            self.update_save_state()
            self.set_status(f"Loaded: {self.filename}")

    def save_file(self):
        if self.filename and self.indentation_applied:
            with open(self.filename, 'w') as file:
                file.write(self.text_display.get("1.0", tk.END).strip())
            messagebox.showinfo("Save", f"File saved as {self.filename}")
            self.set_status(f"Saved: {self.filename}")

    def display_code(self, code):
        self.text_display.config(state="normal")
        self.text_display.delete("1.0", tk.END)
        self.text_display.insert("1.0", code)
        self.text_display.config(state="disabled")

    def reset_indentation(self):
        self.text_display.config(state="normal")
        code = self.text_display.get("1.0", tk.END).strip()
        self.text_display.config(state="disabled")

        # Strip all leading whitespace (including tabs) for a clean reset
        stripped_code = "\n".join(line.lstrip() for line in code.splitlines())
        self.display_code(stripped_code)
        self.indentation_applied = False
        self.update_save_state()
        self.set_status("Indentation reset")

    def apply_indent_from_menu(self):
        """Calls apply_indent with the currently selected number of spaces."""
        self.apply_indent(spaces=self.indent_spaces_var.get())

    def update_indent_spaces_setting(self):
        """Updates the status bar when the indentation space setting is changed."""
        self.set_status(f"Indentation set to {self.indent_spaces_var.get()} spaces for next 'Apply Indent'.")

    def apply_indent(self, spaces=4):
        """
        Applies consistent indentation to the displayed Python code.
        This function uses a heuristic approach to determine indentation levels.
        It handles multi-line strings, parentheses/brackets/braces,
        explicit line continuations with backslashes, and common block keywords.
        """
        self.text_display.config(state="normal")
        code = self.text_display.get("1.0", tk.END).strip()
        self.text_display.config(state="disabled")

        lines = code.splitlines()
        indented_lines = []
        # current_logical_indent: Represents the expected indentation level for the *next* logical block.
        # This changes when a colon is encountered or a block-ending keyword.
        current_logical_indent = 0
        # paren_balance: Tracks open parentheses, brackets, and braces.
        # A positive balance means we are inside a multi-line expression.
        paren_balance = 0
        # in_multiline_string: True if currently inside a triple-quoted string.
        in_multiline_string = False
        # prev_line_ended_with_backslash: True if the previous line ended with an explicit continuation.
        prev_line_ended_with_backslash = False

        for line_num, line in enumerate(lines):
            original_line_content = line # Preserve original content including comments and leading spaces
            stripped_line = line.strip()
            # Remove comments for logic, but keep them for display by using original_line_content.lstrip()
            stripped_for_logic = re.sub(r'#.*$', '', stripped_line).strip()

            if not stripped_for_logic:
                indented_lines.append("")
                prev_line_ended_with_backslash = False # Reset for empty lines
                continue

            # --- Step 1: Handle multi-line strings (docstrings and regular) ---
            # This is a heuristic. It assumes triple quotes are always for multi-line strings.
            # It can be fooled by triple quotes inside single-line strings.
            if '"""' in stripped_for_logic or "'''" in stripped_for_logic:
                # Count occurrences of triple quotes to determine if we enter/exit
                # A single triple-quoted string on one line will flip the state twice, effectively no change.
                if stripped_for_logic.count('"""') % 2 != 0 or stripped_for_logic.count("'''") % 2 != 0:
                    in_multiline_string = not in_multiline_string

            if in_multiline_string:
                # If currently inside a multi-line string, just apply the current logical indent
                # The `lstrip()` ensures we don't preserve original bad indentation.
                indented_lines.append(' ' * (current_logical_indent * spaces) + original_line_content.lstrip())
                prev_line_ended_with_backslash = False # Multi-line strings don't use backslash continuation
                continue

            # --- Step 2: Update parentheses balance for the current line's content ---
            # This affects how the *current* line is visually indented, and the balance for *subsequent* lines.
            paren_balance += stripped_for_logic.count('(')
            paren_balance += stripped_for_logic.count('[')
            paren_balance += stripped_for_logic.count('{')
            paren_balance -= stripped_for_logic.count(')')
            paren_balance -= stripped_for_logic.count(']')
            paren_balance -= stripped_for_logic.count('}')

            # --- Step 3: Determine the base *logical* indent for the *current* line ---
            # This is the indent level based on block structure (if, for, def, etc.)
            # We assume the current line should start at `current_logical_indent` unless it's a dedenting keyword.
            effective_logical_indent_for_this_line = current_logical_indent

            # Check for keywords that imply dedent for *this* line (e.g., elif, else, except, finally)
            # These lines are part of the *previous* block, but shift left.
            if re.match(r"^(elif|else|except|finally)\b", stripped_for_logic):
                if effective_logical_indent_for_this_line > 0:
                    effective_logical_indent_for_this_line -= 1 # Dedent for the keyword itself

            # --- Step 4: Calculate the *visual* indentation for the current line ---
            visual_indent_spaces = effective_logical_indent_for_this_line * spaces

            # If we are inside a parentheses-based continuation or explicit backslash continuation,
            # add an extra visual indent for readability (typically one more level).
            if paren_balance > 0 or prev_line_ended_with_backslash:
                visual_indent_spaces = (effective_logical_indent_for_this_line + 1) * spaces
                
                # Special adjustment for closing parentheses/brackets/braces
                # If the line starts with a closing char and the balance becomes 0 after this line,
                # it should align with the logical indent, not the continuation indent.
                if re.match(r"^[)\]\}]", stripped_for_logic) and paren_balance == 0:
                     visual_indent_spaces = effective_logical_indent_for_this_line * spaces


            # Add the current line to the list with its determined visual indentation
            indented_lines.append(' ' * visual_indent_spaces + original_line_content.lstrip())

            # --- Step 5: Update `current_logical_indent` for the *next* line ---
            # This is the most crucial step for the block structure.
            # It reflects the logical block level for the *next* line.

            # If the current line ends with a colon, the next line should be indented more.
            # This check should only happen if not inside a parentheses-based continuation
            # or if the line does not end with a backslash.
            if stripped_for_logic.endswith(':') and not prev_line_ended_with_backslash and paren_balance == 0:
                # Avoid increasing indent for single-line dictionary/set definitions that end with a colon.
                # This is a heuristic and might not catch all cases (e.g., `dict(a=1, b=2):`).
                if not (stripped_for_logic.startswith(('{', '[')) and stripped_for_logic.endswith(('}', ']')) and ':' in stripped_for_logic):
                    current_logical_indent += 1

            # Update prev_line_ended_with_backslash for the next iteration
            prev_line_ended_with_backslash = stripped_line.endswith('\\')

        formatted_code = "\n".join(indented_lines)
        self.display_code(formatted_code)
        self.indentation_applied = True
        self.update_save_state()
        self.set_status("Indentation applied")

    def update_save_state(self):
        state = "normal" if self.indentation_applied else "disabled"
        self.file_menu.entryconfig("Save", state=state)

    def show_about(self):
        about_text = (
            "Python Indentation\n\n"
            "Program by Dr. Eric O. Flores\n"
            "Month: OCT 2024\n"
            f"Version: {self.version}\n"
            "\n"
            "Copyright GPL3"
        )
        messagebox.showinfo("About", about_text)

    def set_status(self, msg):
        self.status_label.config(text=msg)


# Initialize
if __name__ == "__main__":
    root = tk.Tk()
    app = PythonReindenterApp(root)
    root.mainloop()
