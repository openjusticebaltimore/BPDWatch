const seq_no = $('#court-cases').data('seq-no');

const columnDefs = [
    { field: 'case_number', headerName: 'Case Number' },
    { field: 'case_type', headerName: 'Case Type' },
    { field: 'filing_date', headerName: 'Filing Date' },
    { field: 'status', headerName: 'Status' },
    { field: 'court', headerName: 'Court' },
];

const datasource = {
    getRows(params) {
        fetch(`https://api.mdcaseexplorer.com/api/bpd/seq/${seq_no}`, {
            method: 'post',
            body: JSON.stringify(JSON.stringify(params.request)),
            headers: { 'Content-Type': 'application/json; charset=utf-8' }
        })
        .then(httpResponse => httpResponse.json())
        .then(response => {
            console.log(response);
            params.successCallback(response.rows, response.lastRow);
            resizeCols();
        })
        .catch(error => {
            console.error(error);
            params.failCallback();
        });
    }
};

const gridOptions = {
    columnDefs: columnDefs,
    rowModelType: 'serverSide',
    serverSideDatasource: datasource,
    serverSideStoreType: "partial",
    animateRows: true,
    defaultColDef: {
        resizable: true,
        sortable: true,
        filter: 'agTextColumnFilter',
    }
};

const eGridDiv = document.querySelector('#court-cases');
new agGrid.Grid(eGridDiv, gridOptions);

// auto resize columns
const resizeCols = () => {
    var allColumnIds = [];
    gridOptions.columnApi.getAllColumns().forEach(function (column) {
        allColumnIds.push(column.colId);
    });
    gridOptions.columnApi.autoSizeColumns(allColumnIds);
};