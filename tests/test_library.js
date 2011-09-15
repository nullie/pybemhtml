function tests() {
//    assert(typeof Object.prototype.hasOwnProperty == 'function');

    assert(undefined !== 'undefined');

    assert(undefined + '' === 'undefined');

    assert(!(undefined === 'undefined'));

    a = Array();

    console.log(a);

    a[1.1 - 0.1] = 'bar';

    a[1] = 'bar';

    console.log(a);

    assert(a[1] === 'bar');

    a[-10] = 10;

    assert(a["-10"] === 10);
    assert(a[-10] === 10);

    function bemhtml() {
        return ({"style": (("background:url(" + this["ctx"]["url"]) + ")")});
    }

    bemjson = {
        ctx: {}
    };

    bemhtml.apply(bemjson);

    function bemhtml() {
        return this["block"] === "i-counters" && this["elem"] === "item" && this["_mode"] === "attrs";
    };

    assert(!bemhtml.apply(bemjson));
}
