class Player:
    def __init__(self, name: str,team: list, bag):
        self.name = name
        self.team = team
        self.bag = bag
        self.current_pokemon = team[4]
class Team:
    def __init__(self,team : list):
        self.team = team
