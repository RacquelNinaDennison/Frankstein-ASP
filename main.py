from pyexpat import model
from clingo import Control 
from pathlib import Path 
from  frankstein import Frankenstein

# data 
BASE = Path(__file__).parent 
INSTANCES = BASE/ "src" / "data"
APPLICATIONS = INSTANCES/"application_data.lp"




def main():
    frank = Frankenstein()
    frank.pass_applications(APPLICATIONS)


if __name__ == "__main__":
    main()