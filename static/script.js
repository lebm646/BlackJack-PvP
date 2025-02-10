let player1Name = "";
let player2Name = "";

async function startGame() {
    player1Name = document.getElementById("player1").value || player1Name;
    player2Name = document.getElementById("player2").value || player2Name;
    let bet = parseInt(document.getElementById("bet").value) || 10;

    let response = await fetch("/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ player1: player1Name, player2: player2Name })
    });

    let data = await response.json();
    document.getElementById("message").innerText = data.message;

    updatePlayerUI("player1", data.player1.cards, data.player1.total, data.player1.chips);
    updatePlayerUI("player2", data.player2.cards, data.player2.total, data.player2.chips);

    // Check for immediate Blackjack wins
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

    updatePlayerUI(player, data.cards, data.total);

    // Show winner message if someone won
    if (data.winner) {
        document.getElementById("message").innerText = data.winner;
        disableHitButtons();
    } else if (data.busted) {
        document.getElementById("message").innerText = `${player} busted!`;
        disableHitButtons(player);
    } else if (data.blackjack) {
        document.getElementById("message").innerText = `${player} got Blackjack!`;
        disableHitButtons(player);
    }
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

function updatePlayerUI(player, cards, total) {
    let cardsElement = document.getElementById(player + "-cards");
    cardsElement.innerText = "Cards: " + cards.join(", ");

    document.getElementById(player + "-total").innerText = "Total: " + total;
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

    // Reset UI
    document.getElementById("player1-cards").innerText = "Cards: ";
    document.getElementById("player1-total").innerText = "Total: 0";
    document.getElementById("player2-cards").innerText = "Cards: ";
    document.getElementById("player2-total").innerText = "Total: 0";

    // Enable Hit buttons
    document.querySelectorAll("button").forEach(button => {
        button.disabled = false;
    });

    // Start a new game without asking for names again
    startGame();
}
