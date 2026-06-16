// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract SentinelAI {

    struct ModelRecord {
        bytes32 modelHash;
        address registeredBy;
        uint256 registeredAt;
        string  modelName;
    }

    mapping(bytes32 => ModelRecord) public registeredModels;
    bytes32[] public allModels;

    event ModelRegistered(
        bytes32 indexed modelHash,
        address indexed registeredBy,
        string  modelName,
        uint256 timestamp
    );

    event VerificationPassed(
        bytes32 indexed modelHash,
        address indexed verifier,
        uint256 timestamp
    );

    event VerificationFailed(
        bytes32 indexed expectedHash,
        bytes32 indexed actualHash,
        address indexed verifier,
        uint256 timestamp
    );

    function registerModel(bytes32 _modelHash, string memory _modelName) public {
        require(_modelHash != bytes32(0), "Invalid model hash");
        require(registeredModels[_modelHash].registeredAt == 0, "Model already registered");

        registeredModels[_modelHash] = ModelRecord({
            modelHash:    _modelHash,
            registeredBy: msg.sender,
            registeredAt: block.timestamp,
            modelName:    _modelName
        });

        allModels.push(_modelHash);
        emit ModelRegistered(_modelHash, msg.sender, _modelName, block.timestamp);
    }

    function verifyModel(bytes32 _modelHash) public {
        require(_modelHash != bytes32(0), "Invalid model hash");
        require(registeredModels[_modelHash].registeredAt != 0, "Model not registered");
        emit VerificationPassed(_modelHash, msg.sender, block.timestamp);
    }

    function isModelRegistered(bytes32 _modelHash) public view returns (bool) {
        return registeredModels[_modelHash].registeredAt != 0;
    }

    function getModelDetails(bytes32 _modelHash)
        public
        view
        returns (
            address registeredBy,
            uint256 registeredAt,
            string memory modelName
        )
    {
        ModelRecord memory r = registeredModels[_modelHash];
        return (r.registeredBy, r.registeredAt, r.modelName);
    }

    function getTotalModels() public view returns (uint256) {
        return allModels.length;
    }

    function getModelAtIndex(uint256 _index) public view returns (bytes32) {
        require(_index < allModels.length, "Index out of bounds");
        return allModels[_index];
    }
}
