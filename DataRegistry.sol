// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract PriceDataRegistry {
    // A mapping (like a Python dictionary) to store our hashes
    // Key: Date string (e.g., "2026-02-13")
    // Value: The SHA-256 Hash of the price data
    mapping(string => string) public dataHashes;

    // An event that announces to the network when new data is stored
    event HashStored(string date, string dataHash);

    // The function your Python script will call to save the hash
    function storeHash(string memory date, string memory dataHash) public {
        dataHashes[date] = dataHash;
        
        // Emit the event so it is permanently logged
        emit HashStored(date, dataHash);
    }

    // A function to retrieve a hash for a specific date
    function getHash(string memory date) public view returns (string memory) {
        return dataHashes[date];
    }
}