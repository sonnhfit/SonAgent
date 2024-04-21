from sonagent.enums.rpcmessagetype import RPCMessageType


class IOMsg:
    message = []
    rpc = None

    @staticmethod
    def send_msg(msg: str):  # Remove the 'self' parameter
        msg_type = RPCMessageType.CHAT
        if IOMsg.rpc:  # Use the class name to access the 'rpc' attribute
            IOMsg.rpc.send_msg({  # Use the class name to access the 'rpc' attribute
                'type': msg_type,
                'message': msg
            })
        else:
            print(msg)

    @staticmethod
    def get_input(msg: str):
        IOMsg.message.append(msg)
        return msg
