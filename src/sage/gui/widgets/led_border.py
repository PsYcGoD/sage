"""Psychedelic LED Border Animation for SAGE Desktop GUI."""

import customtkinter as ctk
import math


class LEDBorder(ctk.CTkCanvas):
    """Animated LED border that displays while AI is thinking."""

    def __init__(self, parent, **kwargs):
        """Initialize LED border canvas."""
        super().__init__(
            parent,
            bg="#1a1a1a",  # Match dark theme background (not solid black)
            highlightthickness=0,
            **kwargs
        )

        self.is_animating = False
        self.animation_frame = 0
        self.led_positions = []
        self.led_items = []

        # Psychedelic color palette
        self.colors = [
            "#FF00FF",  # Magenta
            "#00FFFF",  # Cyan
            "#FFFF00",  # Yellow
            "#FF0080",  # Pink
            "#00FF80",  # Mint
            "#8000FF",  # Purple
            "#FF8000",  # Orange
            "#0080FF",  # Blue
        ]

        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, event):
        """Handle window resize."""
        self._calculate_led_positions()

    def _calculate_led_positions(self):
        """Calculate border segments for thin lines."""
        width = self.winfo_width()
        height = self.winfo_height()

        if width <= 1 or height <= 1:
            return

        # Store border dimensions
        self.border_width = width
        self.border_height = height

    def start_animation(self):
        """Start LED animation."""
        if not self.is_animating:
            self.is_animating = True
            self.animation_frame = 0
            self._calculate_led_positions()
            self._animate()

    def stop_animation(self):
        """Stop LED animation."""
        self.is_animating = False
        self.delete("all")

    def _animate(self):
        """Animate continuous flowing gradient border."""
        if not self.is_animating:
            return

        self.delete("all")

        width = self.winfo_width()
        height = self.winfo_height()

        if width <= 1 or height <= 1:
            self.after(50, self._animate)
            return

        border_thickness = 4
        num_colors = len(self.colors)

        # Calculate total perimeter
        perimeter = 2 * (width + height)

        # Each color occupies this much of the perimeter
        segment_size = perimeter / num_colors

        # Draw continuous border with flowing colors
        for i, color in enumerate(self.colors):
            # Calculate start position with animation offset
            start_pos = (i * segment_size + self.animation_frame * 3) % perimeter
            end_pos = (start_pos + segment_size) % perimeter

            # Draw this color segment
            self._draw_border_segment(start_pos, end_pos, perimeter, width, height, color, border_thickness)

        self.animation_frame += 1

        # Continue animation
        self.after(30, self._animate)

    def _draw_border_segment(self, start, end, perimeter, width, height, color, thickness):
        """Draw a continuous border segment."""
        # Handle wrap-around
        if end < start:
            self._draw_border_segment(start, perimeter, perimeter, width, height, color, thickness)
            self._draw_border_segment(0, end, perimeter, width, height, color, thickness)
            return

        # Convert position to coordinates
        points = []
        step = 5  # pixels per step

        for pos in range(int(start), int(end), step):
            if pos < width:
                # Top edge
                points.append((pos, 0))
            elif pos < width + height:
                # Right edge
                points.append((width, pos - width))
            elif pos < 2 * width + height:
                # Bottom edge
                points.append((width - (pos - width - height), height))
            else:
                # Left edge
                points.append((0, height - (pos - 2 * width - height)))

        # Draw line connecting all points
        if len(points) > 1:
            flat_points = [coord for point in points for coord in point]
            self.create_line(flat_points, fill=color, width=thickness, smooth=True)

    def _hex_to_rgba(self, hex_color: str, alpha: float) -> str:
        """Convert hex color to rgba (approximation using stipple)."""
        return hex_color  # Simplified for now


class ThinkingOverlay(ctk.CTkCanvas):
    """LED border overlay that draws only the border, no background fill."""

    def __init__(self, parent, **kwargs):
        """Initialize thinking overlay."""
        super().__init__(
            parent,
            bg="#1a1a1a",  # Match parent background
            highlightthickness=0,
            **kwargs
        )

        self.is_animating = False
        self.animation_frame = 0

        # Psychedelic color palette
        self.colors = [
            "#FF00FF",  # Magenta
            "#00FFFF",  # Cyan
            "#FFFF00",  # Yellow
            "#FF0080",  # Pink
            "#00FF80",  # Mint
            "#8000FF",  # Purple
            "#FF8000",  # Orange
            "#0080FF",  # Blue
        ]

        self.place_forget()  # Hidden by default

    def show(self):
        """Show thinking overlay with animation."""
        # Keep this as a thin activity strip. A full Tk canvas is opaque on
        # Windows and would hide the output text while the model is thinking.
        self.place(x=0, y=0, relwidth=1, height=6)
        self.is_animating = True
        self.animation_frame = 0
        self._animate()

    def hide(self):
        """Hide thinking overlay."""
        self.is_animating = False
        self.delete("all")
        self.place_forget()

    def _animate(self):
        """Animate continuous flowing gradient border."""
        if not self.is_animating:
            return

        self.delete("all")

        width = self.winfo_width()
        height = self.winfo_height()

        if width <= 1 or height <= 1:
            self.after(30, self._animate)
            return

        border_thickness = 4
        num_colors = len(self.colors)

        # Calculate total perimeter
        perimeter = 2 * (width + height)

        # Each color occupies this much of the perimeter
        segment_size = perimeter / num_colors

        # Draw continuous border with flowing colors
        for i, color in enumerate(self.colors):
            # Calculate start position with animation offset
            start_pos = (i * segment_size + self.animation_frame * 3) % perimeter
            end_pos = (start_pos + segment_size) % perimeter

            # Draw this color segment
            self._draw_border_segment(start_pos, end_pos, perimeter, width, height, color, border_thickness)

        self.animation_frame += 1

        # Continue animation
        self.after(30, self._animate)

    def _draw_border_segment(self, start, end, perimeter, width, height, color, thickness):
        """Draw a continuous border segment."""
        # Handle wrap-around
        if end < start:
            self._draw_border_segment(start, perimeter, perimeter, width, height, color, thickness)
            self._draw_border_segment(0, end, perimeter, width, height, color, thickness)
            return

        # Convert position to coordinates
        points = []
        step = 5  # pixels per step

        for pos in range(int(start), int(end), step):
            if pos < width:
                # Top edge
                points.append((pos, 0))
            elif pos < width + height:
                # Right edge
                points.append((width, pos - width))
            elif pos < 2 * width + height:
                # Bottom edge
                points.append((width - (pos - width - height), height))
            else:
                # Left edge
                points.append((0, height - (pos - 2 * width - height)))

        # Draw line connecting all points
        if len(points) > 1:
            flat_points = [coord for point in points for coord in point]
            self.create_line(flat_points, fill=color, width=thickness, smooth=True)
