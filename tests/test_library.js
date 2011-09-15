function tests() {
//    assert(typeof Object.prototype.hasOwnProperty == 'function');

    function bemhtml() {
        return ({"style": (("background:url(" + this["ctx"]["url"]) + ")")});
    }

    bemjson = {
        ctx: {}
    };

    bemhtml.apply(bemjson);
}
