########################
# Calculator Class      #
########################

from decimal import Decimal
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd

from app.calculation import Calculation
from app.calculator_config import CalculatorConfig
from app.calculator_memento import CalculatorMemento
from app.exceptions import OperationError, ValidationError
from app.history import HistoryObserver
from app.input_validators import InputValidator
from app.operations import Operation

# Type aliases for better readability
Number = Union[int, float, Decimal]
CalculationResult = Union[Number, str]


class _SafeFileHandler(logging.Handler):
    """
    A logging handler that avoids Windows file-lock issues by NOT keeping the
    log file open. It opens, writes, and closes on every emit.
    """
    def __init__(self, path: Path, level=logging.INFO):
        super().__init__(level=level)
        self._path = str(path)
        self.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        try:
            os.makedirs(os.path.dirname(self._path), exist_ok=True)
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except Exception:
            # Never raise from logging in app flow
            pass

    def close(self) -> None:
        # Nothing persistent to close (no open handle)
        super().close()


class Calculator:
    """
    Main calculator class implementing multiple design patterns.

    This class serves as the core of the calculator application, managing operations,
    calculation history, observers, configuration settings, and data persistence.
    It integrates various design patterns to enhance flexibility, maintainability, and
    scalability.
    """

    def __init__(self, config: Optional[CalculatorConfig] = None):
        """
        Initialize calculator with configuration.

        Args:
            config (Optional[CalculatorConfig], optional): Configuration settings for the calculator.
                If not provided, default settings are loaded based on environment variables.
        """
        if config is None:
            current_file = Path(__file__)
            project_root = current_file.parent.parent
            config = CalculatorConfig(base_dir=project_root)

        self.config = config
        self.config.validate()

        # Ensure directories exist
        os.makedirs(self.config.log_dir, exist_ok=True)

        # Set up logging (safe on Windows)
        self._setup_logging()

        # Initialize state
        self.history: List[Calculation] = []
        self.operation_strategy: Optional[Operation] = None
        self.observers: List[HistoryObserver] = []
        self.undo_stack: List[CalculatorMemento] = []
        self.redo_stack: List[CalculatorMemento] = []

        self._setup_directories()

        try:
            self.load_history()
        except Exception as e:
            logging.warning(f"Could not load existing history: {e}")

        logging.info("Calculator initialized with configuration")

    def _setup_logging(self) -> None:
        """
        Configure logging so it never holds an open file handle (prevents Windows locks).
        We attach a per-instance safe handler to the ROOT logger so calls like
        logging.info(...) in this module still write to the right file without locks.
        """
        try:
            os.makedirs(self.config.log_dir, exist_ok=True)
            log_file = self.config.log_file.resolve()

            # Root logger setup
            self._root_logger = logging.getLogger()  # root
            self._root_logger.setLevel(logging.INFO)

            # Create and add our safe handler (unique per calculator instance)
            self._safe_handler = _SafeFileHandler(log_file)
            self._root_logger.addHandler(self._safe_handler)

            # Keep a lightweight namespaced logger too (optional)
            self.logger = logging.getLogger(f"calculator.{id(self)}")
            self.logger.setLevel(logging.INFO)
            # No handlers on self.logger; it will propagate to root -> safe handler
            self.logger.propagate = True

            self.logger.info(f"Logging initialized at: {log_file}")
        except Exception as e:
            print(f"Error setting up logging: {e}")
            raise

    def close(self) -> None:
        """
        Detach our handler from the root logger (no open file to close, but keeps things tidy).
        """
        try:
            if hasattr(self, "_root_logger") and hasattr(self, "_safe_handler"):
                try:
                    self._root_logger.removeHandler(self._safe_handler)
                except Exception:
                    pass
                try:
                    self._safe_handler.close()
                except Exception:
                    pass
        finally:
            # Drop references so GC is clear
            if hasattr(self, "_safe_handler"):
                self._safe_handler = None  # type: ignore
            if hasattr(self, "_root_logger"):
                self._root_logger = None  # type: ignore

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def _setup_directories(self) -> None:
        """Create required directories for history management."""
        self.config.history_dir.mkdir(parents=True, exist_ok=True)

    def add_observer(self, observer: HistoryObserver) -> None:
        """Register a new observer."""
        self.observers.append(observer)
        logging.info(f"Added observer: {observer.__class__.__name__}")

    def remove_observer(self, observer: HistoryObserver) -> None:
        """Remove an existing observer."""
        self.observers.remove(observer)
        logging.info(f"Removed observer: {observer.__class__.__name__}")

    def notify_observers(self, calculation: Calculation) -> None:
        """Notify all observers of a new calculation."""
        for observer in self.observers:
            observer.update(calculation)

    def set_operation(self, operation: Operation) -> None:
        """Set the current operation strategy."""
        self.operation_strategy = operation
        logging.info(f"Set operation: {operation}")

    def perform_operation(
        self,
        a: Union[str, Number],
        b: Union[str, Number]
    ) -> CalculationResult:
        """
        Perform calculation with the current operation.
        """
        if not self.operation_strategy:
            raise OperationError("No operation set")

        try:
            validated_a = InputValidator.validate_number(a, self.config)
            validated_b = InputValidator.validate_number(b, self.config)
            result = self.operation_strategy.execute(validated_a, validated_b)

            calculation = Calculation(
                operation=str(self.operation_strategy),
                operand1=validated_a,
                operand2=validated_b
            )

            self.undo_stack.append(CalculatorMemento(self.history.copy()))
            self.redo_stack.clear()
            self.history.append(calculation)

            if len(self.history) > self.config.max_history_size:
                self.history.pop(0)

            self.notify_observers(calculation)
            return result

        except ValidationError as e:
            logging.error(f"Validation error: {str(e)}")
            raise
        except Exception as e:
            logging.error(f"Operation failed: {str(e)}")
            raise OperationError(f"Operation failed: {str(e)}")

    def save_history(self) -> None:
        """
        Save calculation history to a CSV file using pandas.
        """
        try:
            self.config.history_dir.mkdir(parents=True, exist_ok=True)

            history_data = [
                {
                    'operation': str(calc.operation),
                    'operand1': str(calc.operand1),
                    'operand2': str(calc.operand2),
                    'result': str(calc.result),
                    'timestamp': calc.timestamp.isoformat()
                }
                for calc in self.history
            ]

            if history_data:
                df = pd.DataFrame(history_data)
                df.to_csv(self.config.history_file, index=False)
                logging.info(f"History saved successfully to {self.config.history_file}")
            else:
                pd.DataFrame(columns=['operation', 'operand1', 'operand2', 'result', 'timestamp']).to_csv(
                    self.config.history_file, index=False)
                logging.info("Empty history saved")

        except Exception as e:
            logging.error(f"Failed to save history: {e}")
            raise OperationError(f"Failed to save history: {e}")

    def load_history(self) -> None:
        """
        Load calculation history from a CSV file using pandas.
        """
        try:
            if self.config.history_file.exists():
                df = pd.read_csv(self.config.history_file)
                if not df.empty:
                    self.history = [
                        Calculation.from_dict({
                            'operation': row['operation'],
                            'operand1': row['operand1'],
                            'operand2': row['operand2'],
                            'result': row['result'],
                            'timestamp': row['timestamp']
                        })
                        for _, row in df.iterrows()
                    ]
                    logging.info(f"Loaded {len(self.history)} calculations from history")
                else:
                    logging.info("Loaded empty history file")
            else:
                logging.info("No history file found - starting with empty history")
        except Exception as e:
            logging.error(f"Failed to load history: {e}")
            raise OperationError(f"Failed to load history: {e}")

    def get_history_dataframe(self) -> pd.DataFrame:
        """Get calculation history as a pandas DataFrame."""
        return pd.DataFrame([
            {
                'operation': str(calc.operation),
                'operand1': str(calc.operand1),
                'operand2': str(calc.operand2),
                'result': str(calc.result),
                'timestamp': calc.timestamp
            }
            for calc in self.history
        ])

    def show_history(self) -> List[str]:
        """Get formatted history of calculations."""
        return [
            f"{calc.operation}({calc.operand1}, {calc.operand2}) = {calc.result}"
            for calc in self.history
        ]

    def clear_history(self) -> None:
        """Clear calculation history."""
        self.history.clear()
        self.undo_stack.clear()
        self.redo_stack.clear()
        logging.info("History cleared")

    def undo(self) -> bool:
        """Undo the last operation."""
        if not self.undo_stack:
            return False
        memento = self.undo_stack.pop()
        self.redo_stack.append(CalculatorMemento(self.history.copy()))
        self.history = memento.history.copy()
        return True

    def redo(self) -> bool:
        """Redo the previously undone operation."""
        if not self.redo_stack:
            return False
        memento = self.redo_stack.pop()
        self.undo_stack.append(CalculatorMemento(self.history.copy()))
        self.history = memento.history.copy()
        return True
