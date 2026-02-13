class Block:
    """
    Block is a storage container that stores transactions.
    """
    def __init__(self, BlockHeight, BlockSize, BlockHeader, TransactionCount, Transactions):
        self.BlockHeight = BlockHeight
        self.BlockSize = BlockSize
        self.BlockHeader = BlockHeader
        self.TransactionCount = TransactionCount
        self.Transactions = Transactions