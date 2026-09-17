// Behaviour for the "Project + Funding + Phases" create/update page
// (project_inline_form.html, via ProjectCreateInlineView /
// ProjectUpdateInlineView).
//
// Formsets need JavaScript to support adding rows dynamically, because
// Django only renders as many rows as there are forms server-side (the
// existing rows, plus a fixed number of blank "extra" ones). To let the
// user add further funding/phase rows without a page reload, we keep a
// hidden, pre-rendered "empty form" template (each formset's empty_form)
// on the page, and clone it into the visible table whenever
// "Add funding" / "Add phase" is clicked.
function addFormsetRow(tbodySelector, emptyRowSelector, prefix) {
  const tbody = document.querySelector(tbodySelector);

  // Django's management form (the hidden TOTAL_FORMS/INITIAL_FORMS/etc.
  // fields rendered via the formset's management_form) tells the server
  // how many forms to expect. It must be incremented every time a row is
  // added client-side, otherwise the new row is never parsed by the
  // formset on submit (it is simply ignored).
  const totalFormsInput = document.querySelector("#id_" + prefix + "-TOTAL_FORMS");
  const formIndex = parseInt(totalFormsInput.value, 10);

  // The empty form's fields are all named/id'd using the literal
  // placeholder "__prefix__" in place of a form index (e.g.
  // "funding-__prefix__-source"). Replacing every occurrence with the
  // next available index gives the cloned row unique, well-formed field
  // names before it is inserted, so it behaves as a genuine new form in
  // the formset once submitted.
  const emptyRowHtml = document.querySelector(emptyRowSelector).innerHTML;
  const newRowHtml = emptyRowHtml.replace(/__prefix__/g, formIndex);

  tbody.insertAdjacentHTML("beforeend", newRowHtml);
  totalFormsInput.value = formIndex + 1;
}

document.addEventListener("DOMContentLoaded", function () {
  document.getElementById("add-funding").addEventListener("click", function () {
    addFormsetRow("#funding-forms", "#empty-funding-form", "funding");
  });

  document.getElementById("add-phase").addEventListener("click", function () {
    addFormsetRow("#phase-forms", "#empty-phase-form", "phase");
  });
});
