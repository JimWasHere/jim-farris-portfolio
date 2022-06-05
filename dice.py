import random
import requests

dnd_api_url = "https://www.dnd5eapi.co"


class Dice:

    def __init__(self, sides):
        self.sides = sides

    def roll(self):
        return random.randint(1, self.sides)


def dice_roll(number_of_dice, die):
    roll = True
    current_roll = []
    while roll:
        try:
            number_of_dice = int(number_of_dice)
        except ValueError:
            print("Please select a number.")
        else:
            try:
                die = int(die)
            except ValueError:
                print("Please select a number.")
            else:
                print(f"rolling {number_of_dice} d {die}...")
                while len(current_roll) < int(number_of_dice):
                    x = Dice(die).roll()
                    current_roll.append(x)

        roll = False

    return current_roll


response = requests.get(f"{dnd_api_url}/api/classes/paladin").json()

if __name__ == "__main__":
    dice_roll(10, 20)
    print(response)
