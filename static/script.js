let player1Name = "";
let player2Name = "";

async function startGame() {
    player1Name = document.getElementById("player1").value || player1Name;
    player2Name = document.getElementById("player2").value || player2Name;

    let bet = parseInt(document.getElementById("bet").value) || 10;

    let response = await fetch("/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ player1: player1Name, player2: player2Name, bet: bet})
    });

    let data = await response.json();

    if (data.error) {
        alert(data.error);
        return;
    }

    document.getElementById("message").innerText = data.message;

    document.getElementById("player1-name").innerText = player1Name;
    document.getElementById("player2-name").innerText = player2Name;

    // ✅ Make sure chips are not reset
    updatePlayerUI("player1", data.player1.cards, data.player1.total, data.player1.chips);
    updatePlayerUI("player2", data.player2.cards, data.player2.total, data.player2.chips);

    checkGameStatus(data);
}


async function hit(player) {
    let response = await fetch("/hit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ player })
    });

    let data = await response.json();
    console.log("Hit Response:", data);  // Debugging log

    if (data.error) {
        alert(data.error);
        return;
    }

    updatePlayerUI(player, data.cards, data.total, data.chips);
    checkGameStatus(data)
}


function checkGameStatus(data) {
    if (data.busted) {
        document.getElementById("message").innerText = `${data.player} busted!`;
        disableHitButtons();
    } else if (data.blackjack) {
        document.getElementById("message").innerText = `${data.player} got Blackjack!`;
        disableHitButtons();
    } else if (data.winner) {
        document.getElementById("message").innerText = data.winner;
        disableHitButtons();
    }
}

function updatePlayerUI(player, cards, total, chips) {
    document.getElementById(player + "-chips").innerText = "Chips: " + chips;
    document.getElementById(player + "-cards").innerText = "Cards: " + cards.join(", ");
    document.getElementById(player + "-total").innerText = "Total: " + total;

}

async function placeBet(player) {
    let betAmount = parseInt(document.getElementById(player + "-bet").value);
    let response = await fetch("/bet", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ player, bet: betAmount })
    });

    let data = await response.json();
    if (data.error) {
        alert(data.error);
        return;
    }
    document.getElementById(player + "-chips").innerText = "Chips: " + data.chips;
}

function disableHitButtons() {
    document.querySelectorAll("button").forEach(button => {
        if (button.innerText === "Hit") {
            button.disabled = true;
        }
    });
}

async function resetGame() {
    let response = await fetch("/reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" }
    });

    let data = await response.json();
    document.getElementById("message").innerText = data.message;

    // Update chips before starting a new game
    updatePlayerUI("player1", [], 0, data.player1_chips);
    updatePlayerUI("player2", [], 0, data.player2_chips);

    // Enable Hit buttons
    document.querySelectorAll("button").forEach(button => {
        button.disabled = false;
    });

    // Start a new round
    startGame();
}
