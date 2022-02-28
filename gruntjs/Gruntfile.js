
// noinspection JSUnresolvedVariable
module.exports = function(grunt){

  // Project configuration.
  // noinspection JSUnusedGlobalSymbols,JSUnresolvedFunction
  grunt.initConfig({
    concat: {
      css: {
        src: [
          '../static/css/slick.css',
          '../static/css/w3.css',
          '../static/css/w3-theme-black.css',
          '../static/css/custom.css',
        ],
        dest: '../static/built.css',
      },
    },
    cssmin: {
        all: {
            src: '../static/built.css',
            dest: '../static/built.min.css'
        }
    },
    uglify: {
      my_target: {
        files: {
          '../static/js/document_search.min.js': ['../static/js/document_search.js'],
          '../static/js/reader.min.js': ['../static/js/reader.js'],
          '../static/js/search_form.min.js': ['../static/js/search_form.js'],
          '../static/js/sidebar.min.js': ['../static/js/sidebar.js'],
        }
      }
    },
    processhtml: {
      dist: {
        files: {
          '../templates/base.html': ['../templates/base.html'],
          '../templates/network.html': ['../templates/network.html'],
          '../templates/read_article.html': ['../templates/read_article.html'],
          '../templates/read_overview.html': ['../templates/read_overview.html'],
          '../templates/land.html': ['../templates/land.html'],
          '../templates/base_sidebared.html': ['../templates/base_sidebared.html'],
          '../templates/search_corpus.html': ['../templates/search_corpus.html'],
          '../templates/search_document.html': ['../templates/search_document.html'],
        }
      }
    },
    cdnify: {
      someTarget: {
        options: {
          rewriter: function (url) {
            if (url === '/static/js/jquery.min.js') {
              return 'https://ajax.googleapis.com/ajax/libs/jquery/3.2.1/jquery.min.js';
            } else if (url === '/static/js/tippy.all.min.js') {
              return 'https://unpkg.com/tippy.js@2.5.2/dist/tippy.all.min.js'
            } else if (url === '/static/js/intro.min.js') {
              return 'https://cdnjs.cloudflare.com/ajax/libs/intro.js/2.9.3/intro.min.js'
            } else if (url === '/static/css/introjs.min.css') {
              return 'https://cdnjs.cloudflare.com/ajax/libs/intro.js/2.9.3/introjs.min.css'
            } else {
              return url  // all others stay the same.
            }
          }
        },
        files: [{
          expand: true,
          src: '../templates/**/*.html',
        }]
      }
    }
  });

  grunt.loadNpmTasks('grunt-cdnify');
  grunt.loadNpmTasks('grunt-contrib-concat');
  grunt.loadNpmTasks('grunt-css');
  grunt.loadNpmTasks('grunt-processhtml');
  grunt.loadNpmTasks('grunt-contrib-uglify');
  grunt.registerTask('default', ['cdnify', 'concat', 'cssmin', 'uglify', 'processhtml']);
};
