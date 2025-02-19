
function triggerSearch() {
    const searchTitle = document.getElementById("search_title").value;

    fetch(`/search_last_played?term=${encodeURIComponent(searchTitle)}`)
        .then(response => response.json())
        .then(data => {
            if (data.date_played) {
                document.getElementById("search_result").innerHTML = 
                    `Notes: ${data.notes} 
                    <br>Last Played: ${data.date_played}`;
                if (data.notes) {
                    document.getElementById("edit_note_button").style.display = "block";
                    document.getElementById("edit_note_button").setAttribute("data-game-title", searchTitle);
                    document.getElementById("edit_note_button").setAttribute("data-note-id", data.note_id); // Optional if you use IDs
                }
            } else {
                document.getElementById("search_result").innerHTML = "No record found for the specified game.";
                document.getElementById("edit_note_button").style.display = "none";
            }
        });
}

function editNote() {
    const gameTitle = document.getElementById("edit_note_button").getAttribute("data-game-title");
    const currentNote = document.getElementById("search_result").innerText.split('Notes: ')[1]?.split('\n')[0] || '';

    document.getElementById("edit_note_container").style.display = "block";
    document.getElementById("edit_note_input").value = currentNote;
}

function saveNote() {
    const gameTitle = document.getElementById("edit_note_button").getAttribute("data-game-title");
    const updatedNote = document.getElementById("edit_note_input").value;

    fetch(`/update_note`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ game_title: gameTitle, note: updatedNote })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.getElementById("edit_note_container").style.display = "none";
            alert("Note updated successfully!");
        } else {
            alert("Failed to update note.");
        }
    });
}

