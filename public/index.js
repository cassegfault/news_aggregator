function element(string){
	// String based element creation
	// tag at beginning, optional
	// id denoted by #
	// classes denoted by .
	// attributes set like [attr=val] val is optional
	// content goes in parens
	// example: #theid.classname[data-uri='hello-kitty'][hidden].brains(the content goes <i>here</i>)
	const tag_re = /^([a-z0-9]+)/gi,
		  id_re = /\#([a-z0-9\-\_]+)/gi,
		  class_re = /\.([a-z0-9\-\_]+)/gi,
		  attr_re = /\[([^\[\]]+)\]/gi,
		  content_re = /\{([^\(\)]+)\}/gi;
	let tag = string.match(tag_re),
		id = string.match(id_re),
		classNames = string.match(class_re),
		attrs = string.match(attr_re),
		content = string.match(content_re);
	tag = (tag && tag[0]) || "div";
	id = id && id[0].replace('#','');
	content = content && content[0].replace(/[\{\}]/g,'');
	var el = document.createElement(tag);
	if (id)
		el.setAttribute("id",id);
	
	if (classNames && classNames.length > 0)
		classNames.forEach((cl) => el.classList.add(cl.replace('.','')) );
	
	if (attrs && attrs.length > 0){
		attrs.forEach((attr) => {
			let kv = attr.replace(/[\[\]]/g,'').split("=");
			el.setAttribute(kv[0],kv[1] || '');
		});
	}

	if(content)
		el.innerHTML = content;
	return el;
}

/***
  Actual Code
***/


(function iife(){
	var xhr = new XMLHttpRequest();
	xhr.open("GET","http://news.v3x.pw/api/list");
	xhr.onload = function list_ready(){
		buildList(JSON.parse(xhr.response));
	}
	xhr.send();
})();

function make_click_func(post_id, score){
	var fdata = new FormData();
	fdata.append("post_id", post_id);
	fdata.append("score", score);
	return function(){
		var xhr = new XMLHttpRequest();
		xhr.open('POST', 'http://news.v3x.pw/api/rate');
		xhr.send(fdata);
	}
}


function buildList(listData){
	var list_root = document.getElementById("item-list");
	listData.forEach(function list_item_builder(post){
		var root_el = element(".list-item"),
			vote_holder = element(".vote-holder"),
			up_btn = element(".vote.up"),
			down_btn = element(".vote.down"),
			title = element("a.title");

		up_btn.onclick = make_click_func(post['id'], 1);
		down_btn.onclick = make_click_func(post['id'], -1);
		title.innerHTML = `<h2>${post['title']}</h2>`;
		title.href = post['body'];

		vote_holder.appendChild(up_btn);
		vote_holder.appendChild(down_btn);
		root_el.appendChild(vote_holder);
		root_el.appendChild(title);
		list_root.appendChild(root_el);
	});
}