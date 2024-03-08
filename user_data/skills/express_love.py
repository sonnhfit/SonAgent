# filename: express_love.py

from pydantic import BaseModel

class ExpressLove(BaseModel):
    """
    ExpressLove.express_love
    description: return a message expressing love
    args:

    """

    def express_love(self):
        # return a love message
        return "I love you"


if __name__ == "__main__":
    lover = ExpressLove()
    print(lover.express_love())