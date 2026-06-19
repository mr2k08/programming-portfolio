# main.py
import sys
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QGridLayout, QMessageBox


from game_logic import check_winner, update_pos
from bot import botMove


class MorpionUI(QWidget):
    """
    Interface graphique du jeu de morpion.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Morpion")

        # Choix du mode de jeu
        self.two_player_mode = self.ask_game_mode()

        # Plateau de jeu
        self.board = [[' ']*3 for _ in range(3)]

        # Joueur courant (utile uniquement en mode 2 joueurs)
        self.current_player = 'x'

        self.layout = QGridLayout()
        self.buttons = [[None] * 3 for _ in range(3)]

        for row_index in range(3):
            for column_index in range(3):
                button = QPushButton("")
                button.setFixedSize(110, 110)
                button.setStyleSheet("font-size: 36px;")

                button.clicked.connect(
                    lambda _, row=row_index, col=column_index:
                    self.play_turn(row, col)
                )

                self.layout.addWidget(button, row_index, column_index)
                self.buttons[row_index][column_index] = button

        self.setLayout(self.layout)

    def ask_game_mode(self) -> bool:
        """
        Demande le mode de jeu.
        Retourne True pour 2 joueurs, False pour joueur contre bot.
        """
        response = QMessageBox.question(
            self,
            "Mode de jeu",
            "Mode 2 joueurs ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        return response == QMessageBox.StandardButton.Yes

    def play_turn(self, row_index: int, column_index: int) -> None:
        """
        Gère un tour de jeu selon le mode sélectionné.
        """
        if self.board[row_index][column_index] != ' ':
            return

        # -------- MODE 2 JOUEURS --------
        if self.two_player_mode:
            update_pos(self.board, (row_index, column_index), self.current_player)
            self.update_ui(row_index, column_index, self.current_player)

            if check_winner(self.board):
                self.end_game(f"{self.current_player} a gagné")
                return

            if self.is_board_full():
                self.end_game("égalité")
                return

            # Changement de joueur
            self.current_player = 'o' if self.current_player == 'x' else 'x'
            return

        # -------- MODE 1 JOUEUR (BOT) --------
        update_pos(self.board, (row_index, column_index), 'x')
        self.update_ui(row_index, column_index, 'x')

        if check_winner(self.board):
            self.end_game("x a gagné")
            return

        if self.is_board_full():
            self.end_game("égalité")
            return

        bot_row_index, bot_column_index = botMove(self.board)
        update_pos(self.board, (bot_row_index, bot_column_index), 'o')
        self.update_ui(bot_row_index, bot_column_index, 'o')

        if check_winner(self.board):
            self.end_game("o a gagné")

    def update_ui(self, row_index: int, column_index: int, player: str) -> None:
        """
        Met à jour l'affichage après un coup.
        """
        button = self.buttons[row_index][column_index]
        button.setText(player)
        button.setEnabled(False)

    def is_board_full(self) -> bool:
        """
        Vérifie si le plateau est entièrement rempli.
        """
        return all(cell != ' ' for row in self.board for cell in row)

    def end_game(self, message: str) -> None:
        """
        Affiche le résultat et réinitialise la partie.
        """
        QMessageBox.information(self, "Fin de partie", message)
        self.reset_game()

    def reset_game(self) -> None:
        """
        Réinitialise le plateau et l'état du jeu.
        """
        self.board = [[' ']*3 for _ in range(3)]

        self.current_player = 'x'

        for row_index in range(3):
            for column_index in range(3):
                button = self.buttons[row_index][column_index]
                button.setText("")
                button.setEnabled(True)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ui = MorpionUI()
    ui.show()
    sys.exit(app.exec())