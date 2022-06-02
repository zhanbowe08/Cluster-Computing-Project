function(doc) {
    var regs = [/auspol/i, /ausvotes/i];
    var to_emit = false;
    if (doc.tweet.coordinates){
      for (var i in regs) {
        if (regs[i].test(doc.tweet.text)) {
          to_emit = true;
        }
      }
      if (to_emit && doc.sa2 && doc.sentiment.compound){
       emit(["election", doc.sa2], doc.sentiment.compound);
      }
    }
}

function(doc) {
    var regs = [/auspol/i, /ausvotes/i];
    for (var i in regs) {
      if (regs[i].test(doc.doc.text)) {
        emit("election", doc._id);
      }
    }
}
