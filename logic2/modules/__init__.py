"""
SKU Distribution Optimization System

A modular system for optimizing SKU distribution to retail stores
using a two-step approach:
1. Coverage MILP: Maximize color/size coverage for scarce SKUs
2. Quantity ILP: Optimize quantity allocation for all SKUs

Modules:
- data_loader: Data loading and preprocessing
- experiment_config: Experiment scenarios and parameters
- file_manager: Experiment result storage management
- optimizer: Step1 and Step2 optimization logic
- analyzer: Result analysis and evaluation metrics
- visualizer: Visualization capabilities
- experiment_runner: Experiment execution, comparison, and management
"""

__version__ = "1.0.0"
__author__ = "AI Assistant"

# Import main classes for easy access
from .data_loader import DataLoader
from .experiment_config import ExperimentConfig
from .file_manager import FileManager
from .optimizer import SKUOptimizer
from .analyzer import ResultAnalyzer
from .visualizer import ResultVisualizer
from .experiment_runner import ExperimentRunner

__all__ = [
    'DataLoader',
    'ExperimentConfig', 
    'FileManager',
    'SKUOptimizer',
    'ResultAnalyzer',
    'ResultVisualizer',
    'ExperimentRunner'
] 