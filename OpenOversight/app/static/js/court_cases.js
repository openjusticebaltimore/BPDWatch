const seq_no = $('#court-cases').data('seq-no');

fetch('https://api.mdcaseexplorer.com/api/metadata')
    .then(httpResponse => httpResponse.json())
    .then(response => setupGrid(response));

const setupGrid = (metadata) => {
    const columnDefs = [
        {
            field: 'case_number',
            headerName: 'Case Number',
            cellRenderer: 'agGroupCellRenderer'
        },
        {
            field: 'case_type',
            headerName: 'Case Type',
            filter: 'agSetColumnFilter',
            filterParams: {
                values: ['CR', 'Traffic']
            }
        },
        {
            field: 'filing_date',
            headerName: 'Filing Date',
            sortingOrder: ['desc', 'asc', null]
        },
        {
            field: 'status',
            headerName: 'Status',
            filter: 'agSetColumnFilter',
            filterParams: {
                values: metadata.columns.cases.status.allowed_values
            }
        },
        { field: 'court', headerName: 'Court' },
    ];

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
        },
        statusBar: {
            statusPanels: [
              {
                statusPanel: 'customStatusBar',
                key: 'customStatusBarKey',
                align: 'center',
              }
            ]
        },
        masterDetail: true,
        detailRowAutoHeight: true,
        detailCellRenderer: "detailCellRenderer",
        detailCellRendererParams: {
            metadata: metadata
        },
        components: {
            detailCellRenderer: DetailCellRenderer,
            customStatusBar: StatusBar,
        },
        onGridReady: onGridReady
    };

    const eGridDiv = document.querySelector('#court-cases');
    eGridDiv.innerHTML = '';
    new agGrid.Grid(eGridDiv, gridOptions);
};

const onGridReady = event => {
    const columnState = {
        state: [
             {
                colId: 'filing_date',
                sort: 'desc'
            }
        ]
    }
    event.columnApi.applyColumnState(columnState);
};

const datasource = {
    getRows(params) {
        fetch(`https://api.mdcaseexplorer.com/api/bpd/seq/${seq_no}`, {
            method: 'post',
            body: JSON.stringify(JSON.stringify(params.request)),
            headers: { 'Content-Type': 'application/json; charset=utf-8' }
        })
        .then(httpResponse => httpResponse.json())
        .then(response => {
            params.successCallback(response.rows, response.lastRow);
            resizeCols(params.columnApi);
            const statusBarComponent = params.api.getStatusPanel('customStatusBarKey');
            statusBarComponent.updateTotal(params);
        })
        .catch(error => {
            console.error(error);
            params.failCallback();
        });
    }
};

// auto resize columns
const resizeCols = (columnApi) => {
    var allColumnIds = [];
    columnApi.getAllColumns().forEach(function (column) {
        allColumnIds.push(column.colId);
    });
    columnApi.autoSizeColumns(allColumnIds);
};

class StatusBar {
    init(params) {
        this.params = params;
        this.fetching = false;
        this.eGui = document.createElement('div');
        this.eGui.innerHTML = `
            <div class="ag-status-bar-center">
                <div class="ag-status-name-value ag-status-panel ag-status-panel-total-row-count">
                    Total Rows:&nbsp;
                    <span id="total-row-count" class="ag-status-name-value-value">
                        <span class="ag-loading-icon" ref="eLoadingIcon">
                            <span
                                class="ag-icon ag-icon-loading"
                                unselectable="on"
                                role="presentation"
                            ></span>
                        </span>
                    </span>
                </div>
            </div>
        `;
        fetch(`https://api.mdcaseexplorer.com/api/bpd/seq/${seq_no}/total`)
            .then(response => {
                if (typeof response.json === 'function') return response.json();
                else return response;
            })
            .then(response => {
                $('#total-row-count').text(numberWithCommas(response))
            });
    }

    getGui() {
        return this.eGui;
    }

    refresh(params) { return true; }

    updateTotal(params) {
        fetch(`https://api.mdcaseexplorer.com/api/bpd/seq/${seq_no}/total`, {
            method: 'post',
            body: JSON.stringify(params.request),
            headers: { 'Content-Type': 'application/json; charset=utf-8' }
        })
        .then(response => {
            if (typeof response.json === 'function') return response.json();
            else return response;
        })
        .then(response => {
            $('#total-row-count').text(numberWithCommas(response))
        });
    }
}

class DetailCellRenderer {
    init(params) {
        this.params = params;
        this.eGui = document.createElement('div');
        this.eGui.id = 'detail-grid';
        this.eGui.innerHTML = `
            <div
                class="ag-theme-balham"
                style="height: '100%'; backgroundColor: '#ecf0f1'"
            >
                <div class="ag-stub-cell">
                    <span class="ag-loading-icon" ref="eLoadingIcon">
                    <span
                        class="ag-icon ag-icon-loading"
                        unselectable="on"
                    ></span>
                    </span>
                    <span class="ag-loading-text" ref="eLoadingText">
                        Loading...
                    </span>
                </div>
            </div>
        `;
        const detail_loc = params.data.detail_loc.toLowerCase(),
            case_number = params.data.case_number,
            path = `https://api.mdcaseexplorer.com/api/${detail_loc}/${case_number}/full`;
        fetch(path)
            .then(httpResponse => httpResponse.json())
            .then(response => this.render(response));
    }

    getGui() {
        return this.eGui;
    }

    refresh(params) { return true; }

    render(caseData) {
        const detail_loc = caseData.case.detail_loc.toLowerCase(),
            case_number = caseData.case.case_number;
        let top_level = {},
            grids = [];
        for (const [subtable, val] of Object.entries(caseData)) {
            if (typeof val === 'string')
                top_level[subtable] = val;
            else if (Array.isArray(val) && val.length > 0) {
                const subtable_name = `${detail_loc}_${subtable}`,
                    label = toTitleCase(subtable.replace('_', ' ')),
                    id = this.genDetailGridId(subtable_name);
                grids.push({
                    table: subtable_name,
                    label: label,
                    gridOptions: this.genDetailGridOptions(subtable_name, id, val),
                    id: id
                });
            }
        }
        const root_id = this.genDetailGridId(detail_loc);
        grids.unshift({
            table: detail_loc,
            label: `Case Number ${case_number}`,
            gridOptions: this.genDetailGridOptions(detail_loc, root_id, [top_level]),
            id: root_id
        });
        let finalMarkup = '<div class="case-details">';
        for (let i = 0; i < grids.length; i++) {
            finalMarkup += `
            <div>
                <h4>${grids[i].label}</h4>
                <div id="${grids[i].id}"></div>
            </div>
            `;
        }
        finalMarkup += '</div>';
        this.eGui.innerHTML = finalMarkup;
        for (let i = 0; i < grids.length; i++) {
            const eSubGrid = document.querySelector(`#${grids[i].id}`);
            eSubGrid.innerHTML = '';
            new agGrid.Grid(eSubGrid, grids[i].gridOptions);
        }
    }

    genDetailGridId(subtable) {
        return `detailGrid_${this.params.data.case_number}_${subtable}_${this.params.rowIndex}`;
    }

    genDetailGridOptions(table, id, rowData) {
        const sortedColumns = genSortedColumns(this.params.metadata.columns, table);
        let detailGridColumns = [];
        for (const column of sortedColumns) {
            const metadata = column.metadata;
            let detailGridColumn;
            if (
                column.name.endsWith('_str') ||
                column.name === 'id' ||
                column.name === 'case_number'
            )
                continue;
            let columnLabel;
            if (metadata.label === '')
                columnLabel = toTitleCase(column.name);
            else
                columnLabel = metadata.label;
            const tooltipText = metadata.description;
            detailGridColumn = {
                field: column.name,
                headerName: columnLabel,
                headerTooltip: tooltipText,
                width: metadata.width_pixels === null ? 200 : metadata.width_pixels
            };
            detailGridColumns.push(detailGridColumn);
        }
        return {
            columnDefs: detailGridColumns,
            defaultColDef: {
                resizable: true
            },
            rowData: rowData,
            onGridReady: this.setupDetailGrid(id)
        };
    }

    setupDetailGrid(detailGridId) {
        return params => {
            let gridInfo = {
                id: detailGridId,
                api: params.api,
                columnApi: params.columnApi
            };
        
            this.params.api.addDetailGridInfo(detailGridId, gridInfo);
            const detailGrid = document.querySelector(`#${detailGridId}`);
            const detailGridRowsHeight = detailGrid.getElementsByClassName(
                'ag-center-cols-container'
            )[0].offsetHeight;
            const { rowHeight, headerHeight } = params.api.getSizesForCurrentTheme();
            const detailGridHeight = detailGridRowsHeight + headerHeight + 1;
            // resize the detail grid and body viewport to fit the number of rows
            detailGrid.setAttribute('style', `height:${detailGridHeight}px`);
            detailGrid
                .querySelector('.ag-body-viewport')
                .setAttribute('style', `min-height:${detailGridRowsHeight}px`);
        
            // resize expanded row to fit all the detail grids and content
            const expandedRowHeight = detailGrid.closest('.case-details')
                .offsetHeight;
            detailGrid
                .closest('.ag-row')
                .setAttribute(
                    'style',
                    `min-height:${expandedRowHeight}px; transform: translateY(${this.params
                        .rowIndex * rowHeight}px)`
                );
        
            // autoresize columns in detail grids
            params.columnApi.autoSizeAllColumns();
        
            // Collapse other expanded rows
            this.params.api.forEachNode(node => {
                if (node.rowIndex !== this.params.rowIndex - 1 && node.expanded === true)
                node.expanded = false;
            });
        
            // scroll page to show newly expanded row
            setTimeout(() => {
                this.params.api.ensureIndexVisible(
                    this.params.rowIndex - 1,
                    'top'
                );
            }, 500);
        };
    }
}

const genSortedColumns = (metadata, table) => {
    let sortedColumns = [];
    const table_metadata = metadata[table];
    for (const [column, column_metadata] of Object.entries(table_metadata)) {
        if (sortedColumns.length === 0)
            sortedColumns.push({ name: column, metadata: column_metadata });
        else {
            let inserted = false;
            for (let i = 0; i < sortedColumns.length; i++) {
                if (column_metadata.order < sortedColumns[i].metadata.order) {
                    sortedColumns.splice(i, 0, {
                        name: column,
                        metadata: column_metadata
                    });
                    inserted = true;
                    break;
                }
            }
            if (inserted === false)
                sortedColumns.push({ name: column, metadata: column_metadata });
        }
    }
    return sortedColumns;
};

const toTitleCase = str => {
    return str
        .replace(/_/g, ' ')
        .replace(/\w\S*/g, function(txt) {
            return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();
        })
        .replace(/ Id$/, ' ID')
        .replace('Cjis', 'CJIS')
        .replace('Dob', 'DOB');
};

const numberWithCommas = x => {
    return x.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
};