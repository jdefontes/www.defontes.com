YAHOO.util.Event.onDOMReady (function() {

    YAHOO.util.Connect.initHeader("Accept", "application/json", true);
        
    YAHOO.util.Connect.asyncRequest('GET', '/__meta__/', {
        cache: false,
        success: function (o) {
            var resources = YAHOO.lang.JSON.parse(o.responseText);
            var items = [];
            for (i = 0; i < resources.length; ++i) {
                var resource = resources[i];
                items.push({
                    classname: resource['class_name'].toLowerCase(),
                    text: resource['class_name'],
                    onclick: {
                        fn: function (eventType, event, obj) {
                            obj.path = dataTable.currentPath;
                            bindForm(obj, true);
                        },
                        obj: resource
                    }
                });
            }
            var newButton = new YAHOO.widget.Button({
                container: "newButton",
                type: "menu",
                label: "New",
                menu: items
            });
        },
        failure: function () {
            alert("Error loading resource types");
        }
    });

    var columns = [
        {
            key: 'path',
            width: 250,
            formatter: function(el, record) {
                var path = record.getData("path");
                var className = record.getData("class_name");
                if (path == "..") {
                    YAHOO.util.Dom.addClass(el.parentNode, "up");
                } else {
                    YAHOO.util.Dom.addClass(el.parentNode, className.toLowerCase());
                }
                el.innerHTML = '<div style="padding-left: 14px">' + path + '</div>';
            }
        },
        { key: 'title', width: 196},
        { key: 'creation_date', className: "right", formatter: "date", width: 100 },
        { key: 'modification_date', className: "right", formatter: "date", width: 100 }
    ];
    
    var dataSource = new YAHOO.util.XHRDataSource();
    dataSource.responseType = YAHOO.util.DataSource.TYPE_JSON;
    dataSource.connXhrMode = "queueRequests";
    dataSource.responseSchema = {
        resultsList: "child_resources",
        fields: [
            "path",
            "title",
            "class_name",
            { key: "creation_date", parser: "date" },
            { key: "modification_date", parser: "date" }
        ]
    };
    
    var config = {
        height: '145px',
        width: '747px',
        initialLoad: false
    };
    
    var loadForm = function(path) {
        var tran = YAHOO.util.Connect.asyncRequest('GET', path, {
            cache: false,
            success: function (o) {
                bindForm(YAHOO.lang.JSON.parse(o.responseText));
            },
            failure: function () {
                alert("Error getting: " + path);
            }
        });
    };
    
    var formatDate = function(date) {
    	var formatted = [];
    	formatted.push([ "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec" ][date.getUTCMonth()]);
    	formatted.push(" ");
    	formatted.push(date.getUTCDate());
    	formatted.push(", ");
    	formatted.push(date.getUTCFullYear());
    	formatted.push(" ");
		var hours = date.getUTCHours()
    	formatted.push(hours < 10 ? "0" + hours : hours);
    	formatted.push(":");
		var minutes = date.getUTCMinutes()
    	formatted.push(minutes < 10 ? "0" + minutes : minutes);
    	return formatted.join("");
    };
    
    var bindForm = function(resource, isNew) {
        var form = YAHOO.util.Dom.get('edit');
        var inputs = YAHOO.util.Selector.query('input, textarea, select', form);
        YAHOO.util.Dom.batch(inputs, function (el) {
            var wrap = YAHOO.util.Dom.getAncestorByTagName(el, 'div');
            if (resource.hasOwnProperty(el.id)) {
                YAHOO.util.Dom.setStyle(wrap, 'display', 'block');
                if (isNew && el.id == "publication_date") {
                	el.value = formatDate(new Date());
                } else {
                	el.value = resource[el.id] || "";
                }
            } else {
                YAHOO.util.Dom.setStyle(wrap, 'display', 'none');
                el.value = null;
            }
        });
        var thumb = YAHOO.util.Dom.get('thumb');
        if (resource.class_name == "Image" && resource.path != dataTable.currentPath) {
            thumb.src = resource.path + "?w=128&h=128";
            YAHOO.util.Dom.setStyle(thumb, 'display', 'block');
        } else if (resource.class_name == "Artwork" && resource.path != dataTable.currentPath) {
            thumb.src = resource.image_path + "?w=128&h=128";
            YAHOO.util.Dom.setStyle(thumb, 'display', 'block');
        } else {
            thumb.src = null;
            YAHOO.util.Dom.setStyle(thumb, 'display', 'none');
        }
        YAHOO.util.Dom.setStyle(form, 'display', 'block');
    }
    
    var dataTable = new YAHOO.widget.ScrollingDataTable("grid", columns, dataSource, config);
    dataTable.set("selectionMode","single"); 
    dataTable.subscribe("rowMouseoverEvent", dataTable.onEventHighlightRow); 
    dataTable.subscribe("rowMouseoutEvent", dataTable.onEventUnhighlightRow);
    dataTable.subscribe("rowClickEvent", function(args) {
        var record = dataTable.getRecord(args.target);
        var path = record.getData("path");
        var navigateTo = record.getData("parent_path") || path;
        if (path == ".." || record.getData("class_name") == "Folder") {
            loadTable(navigateTo);
        } else {
            dataTable.onEventSelectRow(args);
        }
        loadForm(navigateTo);
    });
    
    var loadTable = function(path) {
        dataSource.sendRequest(path + "?rnd=" + Math.random(), {
            success: function () {
                this.onDataReturnReplaceRows.apply(this,arguments);
                if (path != "/") {
                    var parentPath = path.replace(/\/$/, "");
                    parentPath = parentPath.match(/^.*\//) + "";
                    this.addRow({ path: "..", parent_path: parentPath }, 0);
                }
                this.currentPath = path;
                YAHOO.util.Dom.get('folder').innerHTML = path;
            },
            failure: function () {
                alert("Error navigating to: " + path);
            },
            scope: dataTable
        });
    };

    var flash = function(html) {
        var message = YAHOO.util.Dom.get('message');
        message.innerHTML = html;
        YAHOO.util.Dom.setStyle(message, 'display', 'inline');
        setTimeout(function () { YAHOO.util.Dom.setStyle(message, 'display', 'none'); }, 2000);
    };
    
    var saveButton = new YAHOO.widget.Button("save");
    saveButton.on("click", function () {
        var form = YAHOO.util.Dom.get('edit');
        var path = YAHOO.util.Dom.get('path').value;
        this.set('disabled', true);
        YAHOO.util.Connect.setForm(form, true);
        var tran = YAHOO.util.Connect.asyncRequest('POST', path, {
            upload: function (o) {
                saveButton.set('disabled', false);
                bindForm(YAHOO.lang.JSON.parse(o.responseText));
                flash("Saved successfully");
                // TODO - when we update the current folder we could avoid the extra
                // call to update the table, since we already have the data
                if (path.match("^" + dataTable.currentPath)) loadTable(dataTable.currentPath);
            },
            failure: function () {
                saveButton.set('disabled', false);
                flash("Error - save failed");
            }
        });
    });
    
    var flushButton = new YAHOO.widget.Button("flush");
    flushButton.on("click", function () {
        flushButton.set('disabled', true);
        var tran = YAHOO.util.Connect.asyncRequest('POST', '/admin/', {
            success: function (o) {
                flushButton.set('disabled', false);
                flash("Cache flushed");
            },
            failure: function () {
                flushButton.set('disabled', false);
                flash("Error flushing cache");
            }
        });
    });
    
    YAHOO.util.Event.addListener('image_blob', 'change', function () {
        var file = this.value;
        if (file != null) {
            file = file.substring(file.lastIndexOf('\\')+1); // IE returns full path
            YAHOO.util.Dom.get('path').value = dataTable.currentPath + file;
            YAHOO.util.Dom.get('title').value = file;
        }
    });
    
    // load initial state
    loadTable('/');
    loadForm('/');
    
}); // ready