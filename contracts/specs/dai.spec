// dai.spec

// certoraRun contracts/l2/dai.sol:Dai contracts/specs/HashHelper.sol --verify Dai:contracts/specs/dai.spec --rule_sanity --solc_args "['--optimize','--optimize-runs','200']"

using HashHelper as hashHelper

methods {
    wards(address) returns (uint256) envfree
    name() returns (string) envfree
    symbol() returns (string) envfree
    version() returns (string) envfree
    decimals() returns (uint8) envfree
    totalSupply() returns (uint256) envfree
    balanceOf(address) returns (uint256) envfree
    allowance(address, address) returns (uint256) envfree
    nonces(address) returns (uint256) envfree
    deploymentChainId() returns (uint256) envfree
    PERMIT_TYPEHASH() returns (bytes32) envfree
    DOMAIN_SEPARATOR() returns (bytes32) envfree
    hashHelper.computeDigestForDai(bytes32,bytes32,address,address,uint256,uint256,uint256) envfree
    hashHelper.call_ecrecover(bytes32,uint8,bytes32,bytes32) returns (address) envfree
}

ghost balanceSum() returns mathint {
    init_state axiom balanceSum() == 0;
}

hook Sstore balanceOf[KEY address a] uint256 balance (uint256 old_balance) STORAGE {
    havoc balanceSum assuming balanceSum@new() == balanceSum@old() + balance - old_balance && balanceSum@new() >= 0;
}

invariant balanceSum_equals_totalSupply() balanceSum() == totalSupply()

// Verify that wards behaves correctly on rely
rule rely(address usr) {
    env e;

    rely(e, usr);

    assert(wards(usr) == 1, "Rely did not set the wards as expected");
}

// Verify revert rules on rely
rule rely_revert(address usr) {
    env e;

    uint256 ward = wards(e.msg.sender);

    rely@withrevert(e, usr);

    bool revert1 = ward != 1;
    bool revert2 = e.msg.value > 0;

    assert(revert1 => lastReverted, "Lack of auth did not revert");
    assert(revert2 => lastReverted, "Sending ETH did not revert");
    assert(lastReverted => revert1 || revert2, "Revert rules are not covering all the cases");
}

// Verify that wards behaves correctly on deny
rule deny(address usr) {
    env e;

    deny(e, usr);

    assert(wards(usr) == 0, "Deny did not set the wards as expected");
}

// Verify revert rules on deny
rule deny_revert(address usr) {
    env e;

    uint256 ward = wards(e.msg.sender);

    deny@withrevert(e, usr);

    bool revert1 = ward != 1;
    bool revert2 = e.msg.value > 0;

    assert(revert1 => lastReverted, "Lack of auth did not revert");
    assert(revert2 => lastReverted, "Sending ETH did not revert");
    assert(lastReverted => revert1 || revert2, "Revert rules are not covering all the cases");
}

// Verify that balance behaves correctly on transfer
rule transfer(address to, uint256 value) {
    env e;

    requireInvariant balanceSum_equals_totalSupply();

    uint256 senderBalanceBefore = balanceOf(e.msg.sender);
    uint256 toBalanceBefore = balanceOf(to);
    uint256 supplyBefore = totalSupply();
    bool senderSameAsTo = e.msg.sender == to;

    transfer(e, to, value);

    uint256 senderBalanceAfter = balanceOf(e.msg.sender);
    uint256 toBalanceAfter = balanceOf(to);
    uint256 supplyAfter = totalSupply();

    assert(supplyAfter == supplyBefore, "Supply changed");

    assert(!senderSameAsTo =>
            senderBalanceAfter == senderBalanceBefore - value &&
            toBalanceAfter == toBalanceBefore + value,
            "Transfer did not change balances as expected"
    );

    assert(senderSameAsTo =>
            senderBalanceAfter == senderBalanceBefore,
            "Transfer changed the balance when sender and receiver are the same"
    );
}

// Verify revert rules on transfer
rule transfer_revert(address to, uint256 value) {
    env e;

    uint256 senderBalance = balanceOf(e.msg.sender);
    uint256 toBalance = balanceOf(to);

    transfer@withrevert(e, to, value);

    bool revert1 = to == 0 || to == currentContract;
    bool revert2 = senderBalance < value;
    bool revert3 = e.msg.value > 0;

    assert(revert1 => lastReverted, "Forbidden address didn't revert");
    assert(revert2 => lastReverted, "Insufficient balance didn't revert");
    assert(revert3 => lastReverted, "Sending ETH did not revert");
    assert(lastReverted => revert1 || revert2 || revert3, "Revert rules are not covering all the cases");
}

// Verify that balance and allowance behave correctly on transferFrom
rule transferFrom(address from, address to, uint256 value) {
    env e;

    requireInvariant balanceSum_equals_totalSupply();

    uint256 fromBalanceBefore = balanceOf(e.msg.sender);
    uint256 toBalanceBefore = balanceOf(to);
    uint256 supplyBefore = totalSupply();
    uint256 allowanceBefore = allowance(from, e.msg.sender);
    bool deductAllowance = e.msg.sender != from && allowanceBefore != max_uint256;
    bool fromSameAsTo = from == to;

    transferFrom(e, from, to, value);

    uint256 fromBalanceAfter = balanceOf(e.msg.sender);
    uint256 toBalanceAfter = balanceOf(to);
    uint256 supplyAfter = totalSupply();
    uint256 allowanceAfter = allowance(from, e.msg.sender);

    assert(supplyAfter == supplyBefore, "Supply changed");
    assert(deductAllowance => allowanceAfter == allowanceBefore - value, "Allowance did not decrease in value");
    assert(!deductAllowance => allowanceAfter == allowanceBefore, "Allowance did not remain the same");
    assert(!fromSameAsTo => fromBalanceAfter == fromBalanceBefore - value, "TransferFrom did not decrease the balance as expected");
    assert(!fromSameAsTo => toBalanceAfter == toBalanceBefore + value, "TransferFrom did not increase the balance as expected");
    assert(fromSameAsTo => fromBalanceAfter == fromBalanceBefore, "TransferFrom did not keep the balance the same as expected");
}

// Verify revert rules on transferFrom
rule transferFrom_revert(address from, address to, uint256 value) {
    env e;

    uint256 fromBalance = balanceOf(from);
    uint256 toBalance = balanceOf(to);
    uint256 allowed = allowance(from, e.msg.sender);

    transferFrom@withrevert(e, from, to, value);

    bool revert1 = to == 0 || to == currentContract;
    bool revert2 = fromBalance < value;
    bool revert3 = allowed < value && e.msg.sender != from;
    bool revert4 = e.msg.value > 0;

    assert(revert1 => lastReverted, "Incorrect address did not revert");
    assert(revert2 => lastReverted, "Insufficient balance did not revert");
    assert(revert3 => lastReverted, "Insufficient allowance did not revert");
    assert(revert4 => lastReverted, "Sending ETH did not revert");
    assert(lastReverted => revert1 || revert2 || revert3 || revert4, "Revert rules are not covering all the cases");
}

// Verify that allowance behaves correctly on approve
rule approve(address spender, uint256 value) {
    env e;

    approve(e, spender, value);

    assert(allowance(e.msg.sender, spender) == value, "Approve did not set the allowance as expected");
}

// Verify revert rules on approve
rule approve_revert(address spender, uint256 value) {
    env e;

    approve@withrevert(e, spender, value);

    bool revert1 = e.msg.value > 0;

    assert(revert1 => lastReverted, "Sending ETH did not revert");
    assert(lastReverted => revert1, "Revert rules are not covering all the cases");
}

// Verify that allowance behaves correctly on increaseAllowance
rule increaseAllowance(address spender, uint256 value) {
    env e;

    uint256 spenderAllowance = allowance(e.msg.sender, spender);

    increaseAllowance(e, spender, value);

    assert(allowance(e.msg.sender, spender) == spenderAllowance + value, "increaseAllowance did not increase the allowance as expected");
}

// Verify revert rules on increaseAllowance
rule increaseAllowance_revert(address spender, uint256 value) {
    env e;

    uint256 spenderAllowance = allowance(e.msg.sender, spender);

    increaseAllowance@withrevert(e, spender, value);

    bool revert1 = spenderAllowance + value > max_uint256;
    bool revert2 = e.msg.value > 0;

    assert(revert1 => lastReverted, "Overflow did not revert");
    assert(revert2 => lastReverted, "Sending ETH did not revert");
    assert(lastReverted => revert1 || revert2, "Revert rules are not covering all the cases");
}

// Verify that allowance behaves correctly on decreaseAllowance
rule decreaseAllowance(address spender, uint256 value) {
    env e;

    uint256 spenderAllowance = allowance(e.msg.sender, spender);

    decreaseAllowance(e, spender, value);

    assert(allowance(e.msg.sender, spender) == spenderAllowance - value, "decreaseAllowance did not decrease the allowance as expected");
}

// Verify revert rules on decreaseAllowance
rule decreaseAllowance_revert(address spender, uint256 value) {
    env e;

    uint256 spenderAllowance = allowance(e.msg.sender, spender);

    decreaseAllowance@withrevert(e, spender, value);

    bool revert1 = spenderAllowance - value < 0;
    bool revert2 = e.msg.value > 0;

    assert(revert1 => lastReverted, "Underflow did not revert");
    assert(revert2 => lastReverted, "Sending ETH did not revert");
    assert(lastReverted => revert1 || revert2, "Revert rules are not covering all the cases");
}

// Verify that supply and balance behave correctly on mint
rule mint(address to, uint256 value) {
    env e;

    requireInvariant balanceSum_equals_totalSupply();

    // Save the totalSupply and sender balance before minting
    uint256 supply = totalSupply();
    uint256 toBalance = balanceOf(to);

    mint(e, to, value);

    assert(balanceOf(to) == toBalance + value, "Mint did not increase the balance as expected");
    assert(totalSupply() == supply + value, "Mint did not increase the supply as expected");
}

// Verify revert rules on mint
rule mint_revert(address to, uint256 value) {
    env e;

    // Save the totalSupply and sender balance before minting
    uint256 supply = totalSupply();
    uint256 ward = wards(e.msg.sender);

    mint@withrevert(e, to, value);

    bool revert1 = ward != 1;
    bool revert2 = supply + value > max_uint256;
    bool revert3 = to == 0 || to == currentContract;
    bool revert4 = e.msg.value > 0;

    assert(revert1 => lastReverted, "Lack of auth did not revert");
    assert(revert2 => lastReverted, "Supply overflow did not revert");
    assert(revert3 => lastReverted, "Incorrect address did not revert");
    assert(revert4 => lastReverted, "Sending ETH did not revert");
    assert(lastReverted => revert1 || revert2 || revert3 || revert4, "Revert rules are not covering all the cases");
}

// Verify that supply and balance behave correctly on burn
rule burn(address from, uint256 value) {
    env e;

    requireInvariant balanceSum_equals_totalSupply();

    uint256 supply = totalSupply();
    uint256 fromBalance = balanceOf(from);
    uint256 allowed = allowance(from, e.msg.sender);
    uint256 ward = wards(e.msg.sender);
    bool senderSameAsFrom = e.msg.sender == from;
    bool wardsEqOne = wards(e.msg.sender) == 1;
    bool allowedEqMaxUint = allowed == max_uint256;

    burn(e, from, value);

    assert(!senderSameAsFrom && !wardsEqOne && !allowedEqMaxUint => allowance(from, e.msg.sender) == allowed - value, "Burn did not decrease the allowance as expected" );
    assert(senderSameAsFrom || wardsEqOne || allowedEqMaxUint => allowance(from, e.msg.sender) == allowed, "Burn did not keep the allowance as expected");
    assert(balanceOf(from) == fromBalance - value, "Burn did not decrease the balance as expected");
    assert(totalSupply() == supply - value, "Burn did not decrease the supply as expected");
}

// Verify revert rules on burn
rule burn_revert(address from, uint256 value) {
    env e;

    uint256 supply = totalSupply();
    uint256 fromBalance = balanceOf(from);
    uint256 allowed = allowance(from, e.msg.sender);
    uint256 ward = wards(e.msg.sender);

    burn@withrevert(e, from, value);

    bool revert1 = fromBalance < value;
    bool revert2 = from != e.msg.sender && ward !=1 && allowed < value;
    bool revert3 = e.msg.value > 0;

    assert(revert1 => lastReverted, "Balance underflow did not revert");
    assert(revert2 => lastReverted, "Allowance underflow did not revert");
    assert(revert3 => lastReverted, "Sending ETH did not revert");
    assert(lastReverted => revert1 || revert2 || revert3, "Revert rules are not covering all the cases");
}

// Verify that allowance behaves correctly on permit
rule permit(address owner, address spender, uint256 value, uint256 deadline, uint8 v, bytes32 r, bytes32 s) {
    env e;

    permit(e, owner, spender, value, deadline, v, r, s);

    assert(allowance(owner, spender) == value, "Permit did not set the allowance as expected");
}

// Verify revert rules on permit
rule permit_revert(address owner, address spender, uint256 value, uint256 deadline, uint8 v, bytes32 r, bytes32 s) {
    env e;

    permit@withrevert(e, owner, spender, value, deadline, v, r, s);
    bool permitReverted = lastReverted;
    bool revert1 = e.block.timestamp > deadline;
    bool revert2 = e.msg.value > 0;
    bool revert3 = hashHelper.call_ecrecover(
        hashHelper.computeDigestForDai(DOMAIN_SEPARATOR(), PERMIT_TYPEHASH(), owner, spender, value, nonces(owner), deadline),
        v,
        r,
        s) == owner;
    bool revert4 = owner != 0;

    assert(revert1 => permitReverted, "Deadline exceed did not revert");
    assert(revert2 => permitReverted, "Sending ETH did not revert");
    assert(revert3 => permitReverted, "Wrong signature did not revert");
    assert(revert4 => permitReverted, "Owner must not be 0");
    assert(permitReverted => revert1 || revert2 || revert3 || revert4);
    // TODO: Add the missing revert condition and full coverage for revert cases
}
