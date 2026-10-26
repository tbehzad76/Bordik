(function () {
  const board = document.querySelector("[data-board]");
  if (!board) {
    return;
  }

  const projectId = board.dataset.projectId;
  const csrfMeta = document.querySelector('meta[name="csrf-token"]');
  const csrfToken = csrfMeta ? csrfMeta.content : "";
  let dragged = null;

  function makeDraggable(card) {
    card.setAttribute("draggable", "true");
    card.addEventListener("dragstart", (event) => {
      dragged = card;
      card.classList.add("dragging");
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", card.dataset.cardId);
    });
    card.addEventListener("dragend", () => {
      card.classList.remove("dragging");
      dragged = null;
    });
  }

  board.querySelectorAll("[data-card-id]").forEach(makeDraggable);

  function elementAfter(list, y) {
    const items = Array.from(
      list.querySelectorAll("[data-card-id]:not(.dragging)")
    );
    return items.reduce(
      (closest, child) => {
        const box = child.getBoundingClientRect();
        const offset = y - box.top - box.height / 2;
        if (offset < 0 && offset > closest.offset) {
          return { offset: offset, element: child };
        }
        return closest;
      },
      { offset: Number.NEGATIVE_INFINITY, element: null }
    ).element;
  }

  board.querySelectorAll("[data-column-id]").forEach((column) => {
    const list = column.querySelector("[data-card-list]");
    if (!list) {
      return;
    }

    column.addEventListener("dragover", (event) => {
      event.preventDefault();
      event.dataTransfer.dropEffect = "move";
    });

    column.addEventListener("drop", async (event) => {
      event.preventDefault();
      if (!dragged) {
        return;
      }

      const after = elementAfter(list, event.clientY);
      const siblings = Array.from(
        list.querySelectorAll("[data-card-id]")
      ).filter((card) => card !== dragged);
      const position = after ? siblings.indexOf(after) : siblings.length;

      const url = "/projects/" + projectId + "/cards/" + dragged.dataset.cardId + "/move";
      try {
        const response = await fetch(url, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRF-Token": csrfToken,
          },
          body: JSON.stringify({
            column_id: Number(column.dataset.columnId),
            position: position,
          }),
        });
        if (!response.ok) {
          throw new Error("move failed");
        }
      } catch (error) {
        console.error(error);
      }
      window.location.reload();
    });
  });

  const cardModal = document.getElementById("card-modal");
  if (cardModal) {
    const columnInput = cardModal.querySelector('input[name="column_id"]');

    function openCardModal(columnId) {
      if (columnInput) {
        columnInput.value = columnId;
      }
      if (typeof cardModal.showModal === "function") {
        cardModal.showModal();
      } else {
        cardModal.setAttribute("open", "open");
      }
      const titleInput = cardModal.querySelector('input[name="title"]');
      if (titleInput) {
        titleInput.focus();
      }
    }

    function closeCardModal() {
      if (typeof cardModal.close === "function") {
        cardModal.close();
      } else {
        cardModal.removeAttribute("open");
      }
    }

    document.querySelectorAll("[data-add-card]").forEach((button) => {
      button.addEventListener("click", () => openCardModal(button.dataset.columnId));
    });

    document.querySelectorAll("[data-close-card-modal]").forEach((button) => {
      button.addEventListener("click", closeCardModal);
    });

    cardModal.addEventListener("click", (event) => {
      if (event.target === cardModal) {
        closeCardModal();
      }
    });
  }

  const settingsModal = document.getElementById("project-settings-modal");
  if (settingsModal) {
    function openSettingsModal() {
      if (typeof settingsModal.showModal === "function") {
        settingsModal.showModal();
      } else {
        settingsModal.setAttribute("open", "open");
      }
    }

    function closeSettingsModal() {
      if (typeof settingsModal.close === "function") {
        settingsModal.close();
      } else {
        settingsModal.removeAttribute("open");
      }
    }

    document.querySelectorAll("[data-open-project-settings]").forEach((button) => {
      button.addEventListener("click", openSettingsModal);
    });

    document.querySelectorAll("[data-close-project-settings]").forEach((button) => {
      button.addEventListener("click", closeSettingsModal);
    });

    settingsModal.addEventListener("click", (event) => {
      if (event.target === settingsModal) {
        closeSettingsModal();
      }
    });
  }
})();
