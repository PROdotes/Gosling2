from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QFrame, QHBoxLayout, QSizePolicy
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

# Import GlowButton from the factory
from ..widgets.glow import GlowButton

class ArtistStatsDialog(QDialog):
    """
    Dialog to visualize artist statistics (T-108).
    Shows a pie chart of genre distribution.
    """
    
    def __init__(self, artist_name: str, library_service, parent=None):
        super().__init__(parent)
        self.artist_name = artist_name
        self.library_service = library_service
        
        self.setWindowTitle(f"Statistics: {artist_name}")
        self.resize(600, 500)
        
        # Industrial Amber Compliance: Set Object Name
        self.setObjectName("ArtistStatsDialog")
        
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 1. Header
        header = QLabel(f"Genre Distribution: {self.artist_name}")
        header.setObjectName("ArtistStatsHeader") # Styling via theme.qss
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # 2. Chart Area
        self.canvas_frame = QFrame()
        self.canvas_frame.setObjectName("StatsChartFrame") # Styling via theme.qss
        self.canvas_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        self.canvas_layout = QVBoxLayout(self.canvas_frame)
        
        # Create Matplotlib Figure
        self.figure = Figure(figsize=(5, 4), dpi=100)
        # Note: We must hardcode Matplotlib bg color because it doesn't read QSS
        # But we match it to the theme variable #2d2d2d manually for now
        self.figure.patch.set_facecolor('#2d2d2d') 
        
        self.canvas = FigureCanvas(self.figure)
        # Transparent canvas background to blend with figure
        self.canvas.setStyleSheet("background-color: transparent;")
        
        self.canvas_layout.addWidget(self.canvas)
        layout.addWidget(self.canvas_frame)
        
        # 3. Footer
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()
        
        # Industrial Amber Compliance: Use GlowButton
        self.btn_close = GlowButton("CLOSE")
        self.btn_close.setObjectName("StatsCloseButton")
        self.btn_close.setFixedSize(100, 30)
        self.btn_close.clicked.connect(self.accept)
        
        footer_layout.addWidget(self.btn_close)
        layout.addLayout(footer_layout)

    def _load_data(self):
        """Fetch data from service and plot."""
        stats = self.library_service.get_artist_genre_stats(self.artist_name)
        self._plot_pie_chart(stats)

    def _plot_pie_chart(self, stats: dict):
        self.figure.clear()
        
        bg_color = '#1e1e1e' # Matches #ArtistStatsDialog background
        self.figure.patch.set_facecolor(bg_color)
        
        if not stats:
            ax = self.figure.add_subplot(111)
            ax.set_facecolor(bg_color)
            
            # Hide axes ticks for cleanliness
            ax.set_xticks([])
            ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_visible(False)

            ax.text(0.5, 0.5, "NO GENRE DATA AVAILABLE", 
                    horizontalalignment='center', 
                    verticalalignment='center',
                    color='#888888',
                    fontsize=12,
                    fontweight='bold',
                    transform=ax.transAxes)
            self.canvas.draw()
            return

        # Prepare Data
        labels = list(stats.keys())
        sizes = list(stats.values())
        
        # Sort by size for better visual
        sorted_pairs = sorted(zip(sizes, labels), reverse=True)
        sizes = [s for s, l in sorted_pairs]
        labels = [l for s, l in sorted_pairs]
        
        # Create Plot
        ax = self.figure.add_subplot(111)
        ax.set_facecolor(bg_color)
        
        # Custom colors (Cyber-ish palette)
        colors = ['#ff4444', '#44ff44', '#4444ff', '#ffff44', '#ff44ff', '#44ffff']
        
        wedges, texts, autotexts = ax.pie(
            sizes, 
            labels=labels, 
            autopct='%1.1f%%',
            startangle=90,
            colors=colors[:len(sizes)] if len(sizes) <= len(colors) else None,
            textprops=dict(color="w") # White label text
        )
        
        # Style the autotext (the percentages inside)
        for autotext in autotexts:
            autotext.set_color('black')
            autotext.set_weight('bold')
        
        ax.axis('equal')
        self.canvas.draw()
