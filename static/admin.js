YAHOO.util.Event.onDOMReady (function() {
	
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
		{ key: 'title', width: 212},
		{ key: 'creation_date', className: "right", formatter: "date", width: 100 },
		{ key: 'modification_date', className: "right", formatter: "date", width: 100 }
	];
	
	var dataSource = new YAHOO.util.DataSource("/admin/resources");
	dataSource.responseType = YAHOO.util.DataSource.TYPE_JSON;
	//dataSource.connXhrMode = "queueRequests";
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
		height: '200px',
		initialRequest: "/"
	};
	
	var bindForm = function(path) {
		var tran = YAHOO.util.Connect.asyncRequest('GET', '/admin/resources' + path, {
			cache: false,
			success: function (o) {
				var resource = YAHOO.lang.JSON.parse(o.responseText);
				var form = YAHOO.util.Dom.get('edit');
				var inputs = YAHOO.util.Selector.query('input, textarea', form);
				YAHOO.util.Dom.batch(inputs, function (el) {
					var wrap = YAHOO.util.Dom.getAncestorByTagName(el, 'div');
					if (resource.hasOwnProperty(el.id)) {
						YAHOO.util.Dom.setStyle(wrap, 'display', 'block');
						el.value = resource[el.id];
					} else {
						YAHOO.util.Dom.setStyle(wrap, 'display', 'none');
						el.value = null;
					}
				});
				YAHOO.util.Dom.setStyle(form, 'display', 'block');
			},
			failure: function () {
				alert("Error getting: " + path);
			}
		});
	};
	
	var dataTable = new YAHOO.widget.ScrollingDataTable("grid", columns, dataSource, config);
	dataTable.currentPath = config.initialRequest;
	dataTable.set("selectionMode","single"); 
	dataTable.subscribe("rowMouseoverEvent", dataTable.onEventHighlightRow); 
	dataTable.subscribe("rowMouseoutEvent", dataTable.onEventUnhighlightRow);
	dataTable.subscribe("rowClickEvent", function(args) {
		var record = dataTable.getRecord(args.target);
		var path = record.getData("path");
		var navigateTo = record.getData("parent_path") || path;
		if (path == ".." || record.getData("class_name") == "Folder") {
			bindTable(navigateTo);
		} else {
			dataTable.onEventSelectRow(args);
		}
		bindForm(navigateTo);
	});
	bindForm(config.initialRequest);
	
	var bindTable = function(path) {
		dataSource.sendRequest(path, {
			success: function () {
        		this.onDataReturnReplaceRows.apply(this,arguments);
        		if (path != "/") {
	        		var parentPath = path.replace(/\/$/, "");
	        		parentPath = parentPath.match(/^.*\//) + "";
        			this.addRow({ path: "..", parent_path: parentPath }, 0);
        		}
        		this.currentPath = path;
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
		YAHOO.util.Connect.setForm(form);
		var tran = YAHOO.util.Connect.asyncRequest('POST', '/admin/resources' + path, {
			success: function () {
				saveButton.set('disabled', false);
				flash("Saved successfully");
				if (path.match("^" + dataTable.currentPath)) bindTable(dataTable.currentPath);
			},
			failure: function () {
				saveButton.set('disabled', false);
				flash("Error - save failed");
			}
		});
	});
	
}); // ready