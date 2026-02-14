// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract FarmerPayment {
    address public owner;

    // The constructor runs once when you deploy. You become the owner.
    constructor() {
        owner = msg.sender; 
    }

    // This allows your organization to load funds into the contract.
    // "payable" means this function can receive money.
    function depositFunds() public payable {}

    // The function your Python backend will call to pay the farmer.
    function payFarmer(address payable _farmer, uint256 _amount) public {
        require(msg.sender == owner, "Only the organization can execute payments");
        require(address(this).balance >= _amount, "Insufficient funds in contract");
        
        (bool success, ) = _farmer.call{value: _amount}("");
        require(success, "Transfer failed.");
    }

    // A simple view function to check the contract's current balance.
    function getBalance() public view returns (uint256) {
        return address(this).balance;
    }
}