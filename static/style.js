elemid = null;

function show(idname)
{
    var element = elemid(idname);
    element.style.display='inline';
}

function hide(idname)
{
    var element = elemid(idname);
    element.style.display='none';
}

function update_shared_checkbox(event)
{
    var checkbox = elemid("id_shared");
    var container = elemid("id_add_edit");

    if(checkbox.checked) {
        show("shared_checked");
        hide("shared_unchecked");
        container.classList.remove("private");
    } else {
        show("shared_unchecked");
        hide("shared_checked");
        container.classList.add("private");
    }
}

function clear_add_edit_fields()
{
    for (const id of ["id_big_id", "id_link", "id_title", "id_extended", "id_tags"]) {
        elemid(id).value = "";
    }
}

function enable_add_edit_frame()
{
    var add_frame = elemid("id_add_edit");
    add_frame.style.display = "block";
    document.getElementsByTagName("body")[0].scrollTop = 0;
    elemid("id_add_button").textContent = "-";
}

function on_add_bookmark_clicked(event) {
    var add_frame = elemid("id_add_edit");
    if(add_frame.style.display == "none" || add_frame.style.display == "") {
        enable_add_edit_frame();
    } else {
        elemid("id_add_button").textContent = "+";
        add_frame.style.display = "none";
    }

    clear_add_edit_fields();
    elemid("id_addedit_submit").value = "Add";

    event.preventDefault();
}

function toggle_edit_mode(event)
{
    for(element of document.getElementsByClassName("bookmark_controls")) {
        if(element.style.display == "none" || element.style.display == "") {
            element.style.display = "block";
        } else {
            element.style.display = "none";
        }
    }
    event.preventDefault();
}

function find_big_id(element)
{
    while(!element.hasAttribute("data-big_id"))
        element = element.parentNode;

    return element.getAttribute("data-big_id");
}

function edit_bookmark(event)
{
    const big_id = find_big_id(event.target);
    const bookmark_div = document.querySelector("[data-big_id='" + big_id + "']");

    elemid("id_big_id").value = big_id;
    elemid("id_link").value = bookmark_div.getElementsByClassName("href")[0].textContent;
    elemid("id_title").value = bookmark_div.getElementsByClassName("description")[0].textContent;
    elemid("id_extended").value = bookmark_div.getElementsByClassName("extended")[0].textContent;
    var tags = [];
    for(element of bookmark_div.getElementsByClassName("tag")) {
        tags.push(element.textContent);
    }
    elemid("id_tags").value = tags.join(" ");
    elemid("id_addedit_submit").value = "Update";

    enable_add_edit_frame();
    event.preventDefault();
}

function delete_bookmark(event)
{
    var big_id = find_big_id(event.target);
    fetch("/bookmark", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({"big_id": big_id})
    }).then(response => response.json())
    .then(data => {
        if(data.deleted === true) {
            const bookmark_div = document.querySelector("[data-big_id='" + big_id + "']");
            bookmark_div.style.display = 'none';
        }
    });

    event.preventDefault();
}

function show_login_form(event)
{
    event.preventDefault();

    elemid("id_div_log_in").style.display = "block";
    elemid("id_username").focus();
}

function add_edit_submit(event)
{
    event.preventDefault();

    var add_edit_dict = {
        big_id: elemid("id_big_id").value,
        link: elemid("id_link").value,
        title: elemid("id_title").value,
        extended: elemid("id_extended").value,
        tags: elemid("id_tags").value,
        shared: elemid("id_shared").checked ? "yes" : "no",
    }

    fetch("/bookmark", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(add_edit_dict)
    }).then(response => response.json())
    .then(data => {
        if(data.updated === true) {
            //console.log("Would add ");
            // console.log(data);
            // TODO rather than refresh, update the DOM (and clear the form!).
            window.location.reload();
        }
    });
    return false;
}

function init_bookmark_editors()
{
    for(element of document.getElementsByClassName("bookmark_edit")) {
        element.addEventListener("click", edit_bookmark);
    }

    for(element of document.getElementsByClassName("bookmark_delete")) {
        element.addEventListener("click", delete_bookmark);
    }
}

function init(event)
{
    elemid = document.getElementById.bind(document);

    /* Add / edit bookmark submission */
    elemid("id_addedit_submit").addEventListener("click", add_edit_submit);

    /* "shared" padlock */
    update_shared_checkbox();
    elemid("id_shared").addEventListener("click", update_shared_checkbox);

    /* "+" toggle button */
    elemid("id_add_button").addEventListener("click", on_add_bookmark_clicked);

    /* "Edit" toggle button */
    elemid("id_edit_button").addEventListener("click", toggle_edit_mode);
    init_bookmark_editors();

    /* Logging in */
    if(elemid("id_a_log_in") !== null)
        elemid("id_a_log_in").addEventListener("click", show_login_form);
}

